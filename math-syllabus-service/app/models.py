from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class GradeEnum(str, Enum):
  primary = "primary"
  secondary = "secondary"
  college = "college"

class DifficultyEnum(str, Enum):
  easy = "easy"
  medium = "medium"
  hard = "hard"

class LessonsRequest(BaseModel):
  topic_title: str = Field(..., example="Addition")
  grade: GradeEnum
  difficulty_level: DifficultyEnum
  number_of_lessons: int = Field(..., gt=0, le=5)

class LessonContentRequest(BaseModel):
  topic_title: str = Field(..., example="Addition")
  lesson_title: str
  grade: GradeEnum
  difficulty_level: DifficultyEnum
  exercises_count: int = Field(..., gt=0, le=5)
  quiz_count: int = Field(..., gt=0, le=5)

class Lesson(BaseModel):
  lesson_number: int
  title: str
  introduction: str
  explanation: str
  worked_examples: List[dict]
  tips: List[str]
  common_mistakes: List[str]
  practice_exercises: List[dict]
  quiz: List[dict]

class LessonsListResponse(BaseModel):
  topic: str
  grade: GradeEnum
  difficulty_level: DifficultyEnum
  lessons: List[str]

class LessonContentResponse(BaseModel):
  lesson: Lesson
