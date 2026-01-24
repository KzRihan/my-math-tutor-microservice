from fastapi import FastAPI, HTTPException
import json
import re
import logging

from app.models import (
  LessonsRequest,
  LessonContentRequest,
  LessonsListResponse,
  LessonContentResponse,
  Lesson
)
from app.llm import generate_text

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Syllabus Service")

def clean_json_text(text: str) -> str:
  """
  Clean common JSON formatting issues that LLMs sometimes introduce.
  """
  # Remove trailing commas before closing braces/brackets
  text = re.sub(r',(\s*[}\]])', r'\1', text)
  # Remove comments (not standard JSON but sometimes LLMs add them)
  text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
  text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
  return text.strip()

def extract_json(text: str) -> dict:
  """
  Robustly extract JSON object from LLM output.
  Handles markdown code blocks, extra text, and multiple JSON objects.
  """
  if not text or not text.strip():
    raise ValueError("Empty response from LLM")
  
  # First, try to extract JSON from markdown code blocks
  # Pattern: ```json ... ``` or ``` ... ```
  markdown_patterns = [
    r"```json\s*\n(.*?)\n```",
    r"```\s*\n(.*?)\n```",
    r"```json\s*(.*?)```",
    r"```\s*(.*?)```",
  ]
  
  for pattern in markdown_patterns:
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
      try:
        cleaned = clean_json_text(match.group(1).strip())
        return json.loads(cleaned)
      except json.JSONDecodeError:
        continue
  
  # If no markdown block found, try to find JSON objects directly
  # Use a more robust approach: find balanced braces
  json_candidates = []
  start_idx = 0
  
  while True:
    # Find the next opening brace
    start_brace = text.find('{', start_idx)
    if start_brace == -1:
      break
    
    # Find the matching closing brace by counting braces
    brace_count = 0
    end_brace = -1
    
    for i in range(start_brace, len(text)):
      if text[i] == '{':
        brace_count += 1
      elif text[i] == '}':
        brace_count -= 1
        if brace_count == 0:
          end_brace = i
          break
    
    if end_brace != -1:
      json_candidate = text[start_brace:end_brace + 1]
      try:
        cleaned = clean_json_text(json_candidate)
        parsed = json.loads(cleaned)
        json_candidates.append(parsed)
      except json.JSONDecodeError:
        pass
      start_idx = end_brace + 1
    else:
      break
  
  # Return the first valid JSON object found
  if json_candidates:
    logger.info(
      f"Successfully extracted JSON from "
      f"{len(json_candidates)} candidate(s)"
    )
    return json_candidates[0]
  
  # Last resort: try the old regex method (but non-greedy)
  match = re.search(r"\{.*?\}", text, re.DOTALL)
  if match:
    try:
      cleaned = clean_json_text(match.group())
      return json.loads(cleaned)
    except json.JSONDecodeError as e:
      logger.error(f"Failed to parse JSON with regex: {e}")
      raise ValueError(
        f"Found JSON-like structure but failed to parse: {str(e)}"
      )
  
  # If all else fails, log the response for debugging
  logger.error(
    f"Could not extract JSON from LLM response. "
    f"Response preview: {text[:500]}"
  )
  raise ValueError(
    "No valid JSON object found in LLM response. "
    "The response may contain markdown formatting or extra text. "
    f"Response preview: {text[:200]}..."
  )

@app.post("/generate-lessons", response_model=LessonsListResponse)
async def generate_lessons(payload: LessonsRequest):
  """
  Generate lesson titles only (list of strings) for a topic
  """
  try:
    system_prompt = """You are a helpful assistant that generates \
educational content. 
CRITICAL RULES:
1. You must respond with ONLY valid JSON
2. Do not include any markdown formatting, code blocks, explanations, \
or additional text
3. Output raw JSON only
4. Follow ALL instructions precisely, especially regarding exact counts \
and numbers"""

    # Create example lessons array based on actual number requested
    example_lessons = [
      f'"Lesson {i+1} title"' 
      for i in range(payload.number_of_lessons)
    ]
    example_lessons_str = ", ".join(example_lessons)
    
    user_prompt = f"""Generate EXACTLY {payload.number_of_lessons} \
lesson title(s) for the topic '{payload.topic_title}', \
grade '{payload.grade}', difficulty '{payload.difficulty_level}'. 

MANDATORY REQUIREMENTS (YOU MUST FOLLOW THESE EXACTLY):
- Generate EXACTLY {payload.number_of_lessons} lesson title(s) - \
this is NOT optional
- Do NOT generate more than {payload.number_of_lessons} lesson(s)
- Do NOT generate fewer than {payload.number_of_lessons} lesson(s)
- Each lesson title should be a descriptive, educational string
- The "lessons" array must contain EXACTLY \
{payload.number_of_lessons} string element(s)

Return ONLY a valid JSON object in this exact format \
(no markdown, no code blocks, no extra text):

{{
  "topic": "{payload.topic_title}",
  "grade": "{payload.grade}",
  "difficulty_level": "{payload.difficulty_level}",
  "lessons": [{example_lessons_str}]
}}

VERIFICATION: Before responding, count the items in your "lessons" \
array. It must be exactly {payload.number_of_lessons}.

Remember: 
- Output ONLY the JSON object, nothing else
- The "lessons" array must have exactly \
{payload.number_of_lessons} item(s) - verify this before responding"""
    
    # Try up to 2 times if count doesn't match
    max_attempts = 2
    current_user_prompt = user_prompt
    
    for attempt in range(max_attempts):
      full_prompt = f"{system_prompt}\n\n{current_user_prompt}"
      raw_output = await generate_text(full_prompt)
      logger.debug(
        f"Raw LLM output (attempt {attempt + 1}): {raw_output[:500]}"
      )
      syllabus_json = extract_json(raw_output)

      # Ensure lessons is a list of strings
      lesson_titles = []
      for l in syllabus_json.get("lessons", []):
        if isinstance(l, str):
          lesson_titles.append(l)
        elif isinstance(l, dict) and "title" in l:
          lesson_titles.append(l["title"])
        else:
          lesson_titles.append(str(l))
      
      # Validate and enforce exact number of lessons
      if len(lesson_titles) != payload.number_of_lessons:
        if attempt < max_attempts - 1:
          logger.warning(
            f"LLM returned {len(lesson_titles)} lessons but "
            f"{payload.number_of_lessons} was requested "
            f"(attempt {attempt + 1}). Retrying with stricter prompt..."
          )
          # Add a more emphatic reminder for retry
          current_user_prompt = (
            user_prompt + 
            f"\n\nIMPORTANT: Your previous response had "
            f"{len(lesson_titles)} lesson(s), but you MUST return "
            f"exactly {payload.number_of_lessons} lesson(s). "
            f"Please try again."
          )
          continue
        else:
          # Last attempt failed, use fallback logic
          logger.warning(
            f"LLM returned {len(lesson_titles)} lessons but "
            f"{payload.number_of_lessons} was requested after "
            f"{max_attempts} attempts. "
            f"Using fallback: truncating/limiting to requested count."
          )
          # Take only the requested number
          # (truncate if too many, pad if too few)
          if len(lesson_titles) > payload.number_of_lessons:
            lesson_titles = lesson_titles[:payload.number_of_lessons]
          elif len(lesson_titles) < payload.number_of_lessons:
            logger.error(
              f"LLM returned fewer lessons ({len(lesson_titles)}) "
              f"than requested ({payload.number_of_lessons})"
            )
            # Pad with generic titles if needed
            while len(lesson_titles) < payload.number_of_lessons:
              lesson_titles.append(
                f"Lesson {len(lesson_titles) + 1}"
              )
      
      # If we got the right count, break out of retry loop
      break

    return LessonsListResponse(
      topic=syllabus_json.get("topic", payload.topic_title),
      grade=payload.grade,
      difficulty_level=payload.difficulty_level,
      lessons=lesson_titles
    )

  except ValueError as e:
    logger.error(f"JSON extraction failed: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=(
        f"Failed to extract valid JSON from LLM response: {str(e)}"
      )
    )
  except json.JSONDecodeError as e:
    logger.error(f"JSON parsing error: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"Invalid JSON format in LLM response: {str(e)}"
    )
  except Exception as e:
    logger.error(
      f"Unexpected error in generate_lessons: {str(e)}", 
      exc_info=True
    )
    raise HTTPException(
      status_code=500, 
      detail=f"Internal server error: {str(e)}"
    )

@app.post("/generate-lesson-content", response_model=LessonContentResponse)
async def generate_lesson_content(payload: LessonContentRequest):
  """
  Generate full lesson content for a single lesson
  """
  try:
    system_prompt = """You are a helpful assistant that generates \
educational content. 
CRITICAL: You must respond with ONLY valid JSON. Do not include any \
markdown formatting, code blocks, explanations, or additional text. \
Output raw JSON only."""

    user_prompt = f"""Create a full lesson for topic \
'{payload.topic_title}' with title '{payload.lesson_title}', \
grade '{payload.grade}', difficulty '{payload.difficulty_level}'. \
Include:
- Introduction (minimum 5 sentences)
- Detailed Explanation
- Worked examples (include steps as strings in arrays)
- Tips (array of strings)
- Common mistakes (array of strings)
- Practice exercises (exactly {payload.exercises_count} exercises)
- Quiz (exactly {payload.quiz_count} questions)

STRICT RULES:
- Introduction: minimum 5 sentences
- Explanation: Must be detailed and comprehensive
- Worked examples: array of objects with steps
- Practice exercises: exactly {payload.exercises_count} exercises \
as objects
- Quiz questions: exactly {payload.quiz_count} questions as objects
- No field can be empty

Return ONLY a valid JSON object in this exact format \
(no markdown, no code blocks, no extra text):

{{
  "lesson_number": 1,
  "title": "{payload.lesson_title}",
  "introduction": "Detailed introduction text here...",
  "explanation": "Detailed explanation text here...",
  "worked_examples": [{{"problem": "...", "solution": "...", \
"steps": ["step1", "step2"]}}],
  "tips": ["tip1", "tip2"],
  "common_mistakes": ["mistake1", "mistake2"],
  "practice_exercises": [{{"question": "...", "answer": "..."}}],
  "quiz": [{{"question": "...", "options": ["A", "B", "C"], \
"correct": "A"}}]
}}

Remember: Output ONLY the JSON object, nothing else."""
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    raw_output = await generate_text(full_prompt)
    logger.debug(f"Raw LLM output: {raw_output[:500]}")
    lesson_json = extract_json(raw_output)

    lesson_obj = Lesson(**lesson_json)
    return LessonContentResponse(lesson=lesson_obj)

  except ValueError as e:
    logger.error(f"JSON extraction failed: {str(e)}")
    raise HTTPException(
      status_code=500, 
      detail=(
        f"Failed to extract valid JSON from LLM response: {str(e)}"
      )
    )
  except json.JSONDecodeError as e:
    logger.error(f"JSON parsing error: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail=f"Invalid JSON format in LLM response: {str(e)}"
    )
  except Exception as e:
    logger.error(
      f"Unexpected error in generate_lesson_content: {str(e)}", 
      exc_info=True
    )
    raise HTTPException(
      status_code=500, 
      detail=f"Internal server error: {str(e)}"
    )
