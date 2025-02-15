from pydantic import BaseModel, Field
from typing import List, Optional 




class KeySectionInfo(BaseModel):
    relevance_score: int = Field(
        ..., ge=1, le=10, description="Score from 1-10 indicating relevance to job"
    )
    key_points: List[str] = Field(..., description="List of important points to cover")
    required_knowledge: List[str] = Field(
        ..., description="Specific knowledge areas to assess"
    )
    candidate_experience: str = Field(
        ..., description="Relevant experience from candidate's resume"
    )
    suggested_focus: str = Field(
        ..., description="Recommended focus areas for interview"
    )


class InterviewSections(BaseModel):
    technical_skills: KeySectionInfo
    system_design: KeySectionInfo
    problem_solving: KeySectionInfo
    domain_knowledge: KeySectionInfo
    project_experience: KeySectionInfo

class QuestionDetail(BaseModel):
    question: str = Field(..., description="The interview question")
    model_answer: str = Field(
        ...,
        description="Complete model answer that demonstrates ideal response",
        min_length=50
    )
    expected_answer_points: List[str] = Field(..., description="Key points that should be covered in the answer")

class SectionQuestions(BaseModel):
    technical_knowledge: List[QuestionDetail] = Field(..., 
                                                      description="Questions about technical skills and knowledge")
    system_design: List[QuestionDetail] = Field(..., 
                                                description="System design and architecture questions")
    problem_solving: List[QuestionDetail] = Field(..., 
                                                  description="Algorithmic and logical problem-solving questions")
    coding_challenge: List[QuestionDetail] = Field(..., 
                                                   description="Programming implementation questions")


class Feedback(BaseModel):
    type: str = Field(
        ..., 
        description="Type of feedback: 'positive' or 'negative'",
        pattern='^(positive|negative)$'
    )
    points: List[str] = Field(
        ...,
        description="List of feedback points",
        min_items=1
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Improvement suggestions when feedback is negative"
    )
    missing_points: Optional[List[str]] = Field(
        default=None,
        description="Points that were missing from the answer"
    )

class EvaluationResult(BaseModel):
    score: float = Field(
        ...,
        description="Score out of 10",
        ge=0,
        le=10
    )
    feedback: Feedback = Field(
        ...,
        description="Structured feedback containing positive/negative points and suggestions"
    )


class SectionFeedback(BaseModel):
    score: int = Field(description="The user's score out of 10 for this section.")
    points_included: List[str] = Field(description="Points the user covered in their answers.")
    missing_points: List[str] = Field(description="Points the user missed in their answers.")
    suggestions: List[str] = Field(description="Suggestions to improve competency in this section.")

class OverallResult(BaseModel):
    technical_knowledge: SectionFeedback = Field(description="Feedback for the Technical Knowledge section.")
    system_design: SectionFeedback = Field(description="Feedback for the System Design section.")
    problem_solving: SectionFeedback = Field(description="Feedback for the Problem Solving section.")