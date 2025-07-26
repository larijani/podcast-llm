"""
Pydantic models for podcast generation.

This module defines the core data models used throughout the podcast generation system.
It uses Pydantic for data validation and serialization, providing type safety and
structured representations of podcast components like outlines, scripts, and research
materials.

Key models include:
- PodcastOutline: Complete episode structure with sections and subsections
- PodcastSection: Major content sections within an episode
- PodcastSubsection: Detailed subsections of content
- Script: Complete podcast script with speaker turns
- Question/Answer: Individual conversation exchanges
- WikipediaPages: Research material from Wikipedia
- SearchQueries: Web search queries for additional research

The models enforce consistent structure and provide helper methods for formatting
and manipulating podcast content. They serve as the foundational data structures
that flow through the generation pipeline.

Example:
    outline = PodcastOutline(
        sections=[
            PodcastSection(
                title="Introduction",
                subsections=[
                    PodcastSubsection(title="Topic Overview"),
                    PodcastSubsection(title="Key Concepts")
                ]
            )
        ]
    )
    print(outline.as_str)
"""

from typing import List
from pydantic import BaseModel, Field


class ContextDocument(BaseModel):
    title: str = Field(description="The title of the document")
    text: str = Field(description="The text of the document")
    source: str = Field(description="The source of the document")


class PodcastSubsection(BaseModel):
    """
    A model representing a subsection within a podcast section.

    This class models an individual subsection of content within a larger podcast section.
    It provides a structured way to store and format subsection titles, with a helper
    property to output the subsection in a standardized string format with appropriate
    indentation.

    Attributes:
        title (str): The title/heading text for this subsection
    """
    title: str = Field(..., description="A subsection in a podcast outline")

    @property
    def as_str(self) -> str:
        return f"-- {self.title}".strip()


class PodcastSection(BaseModel):
    """
    A model representing a section within a podcast outline.

    This class models a major section of content within a podcast outline. Each section
    contains a title and a list of subsections, providing hierarchical structure to
    the podcast content. A helper property formats the section and its subsections
    into a standardized string representation.

    Attributes:
        title (str): The title/heading text for this section
        subsections (List[PodcastSubsection]): List of subsections contained within this section
    """
    title: str = Field(..., description="A section in a podcast outline")
    subsections: List[PodcastSubsection] = Field(..., description="List of subsections in a podcast section")

    @property
    def as_str(self) -> str:
        return f"{self.title}\n{'\n'.join([ss.as_str for ss in self.subsections])}".strip()


class PodcastOutline(BaseModel):
    """
    A model representing a complete podcast episode outline.

    This class models the full structure of a podcast episode outline, containing
    an ordered list of major sections, each with their own subsections. It provides
    a hierarchical organization of the episode content and includes a helper property
    to format the entire outline into a standardized string representation.

    Attributes:
        sections (List[PodcastSection]): Ordered list of major sections making up the episode outline
    """
    sections: List[PodcastSection] = Field(..., description="List of sections in a podcast outline")
    
    @property
    def as_str(self) -> str:
        return f"{'\n'.join([s.as_str for s in self.sections])}".strip()



class WikipediaPage(BaseModel):
    """A single suggested Wikipedia page."""
    name: str = Field(..., description="The exact title of the Wikipedia page")
    reason: str = Field(..., description="A brief explanation of why this page is relevant")


class WikipediaPages(BaseModel):
    """A list of suggested Wikipedia pages."""
    pages: List[WikipediaPage] = Field(..., description="A list of suggested Wikipedia pages")


class SummarizedDocument(BaseModel):
    """A summarized document with key topics."""
    summary: str = Field(..., description="A dense, informative summary of the document, focused on the key topics.")

class SearchQuery(BaseModel):
    """A single suggested search query."""
    query: str = Field(..., description="The exact search query to be used")

    @property
    def as_str(self) -> str:
        return f"### {self.query}".strip()
    

class SearchQueries(BaseModel):
    """
    A model representing a collection of search queries.

    This class models a collection of search queries used to gather research material for
    podcast content generation. It stores a list of SearchQuery objects and provides a
    structured way to work with multiple queries together.

    Attributes:
        queries (List[SearchQuery]): List of SearchQuery objects representing the collection
    """
    queries: List[SearchQuery] = Field(..., title="List of search queries")



class Question(BaseModel):
    """
    A model representing a question in an interview conversation.

    This class models an individual question asked by an interviewer in a podcast conversation.
    It provides a structured way to store and format question text, with a helper property
    to output the question in a standardized string format.

    Attributes:
        question (str): The actual text content of the question being asked
    """
    question: str = Field(..., title="Text of the question")

    @property
    def as_str(self) -> str:
        return f"{self.question}".strip()


class Answer(BaseModel):
    """
    A model representing an answer in an interview conversation.

    This class models an individual answer given by an interviewee in a podcast conversation.
    It provides a structured way to store and format answer text, with a helper property
    to output the answer in a standardized string format.

    Attributes:
        answer (str): The actual text content of the answer being given
    """
    answer: str = Field(..., title="Text of the answer")

    @property
    def as_str(self) -> str:
        return f"{self.answer}".strip()


class ScriptLine(BaseModel):
    """
    A model representing a single line of dialogue in a podcast script.

    This class models an individual line of dialogue from either the interviewer or 
    interviewee in a podcast conversation. It provides a structured way to store both
    the speaker identifier and their dialogue text, with a helper property to format
    the line in a standardized string format.

    Attributes:
        speaker (str): Identifier for who is speaking ('Interviewer' or 'Interviewee')
        text (str): The actual dialogue content being spoken
    """
    speaker: str = Field(..., title="The person speaking")
    text: str = Field(..., title="A line in a podcast script.")

    @property
    def as_str(self) -> str:
        return f"{self.speaker}: {self.text}".strip()


class Script(BaseModel):
    """
    A model representing a complete podcast script.

    This class models the full script of a podcast episode, containing an ordered list
    of dialogue lines from both interviewer and interviewee. It provides a structured
    way to store the complete conversation and includes a helper property to format
    the entire script into a standardized string representation with proper speaker
    labels and spacing.

    Attributes:
        lines (List[ScriptLine]): Ordered list of dialogue lines making up the complete script
    """
    lines: List[ScriptLine] = Field(..., title="Lines in a podcast script")

    @property
    def as_str(self) ->  str:
        return '\n\n'.join([l.as_str for l in self.lines])
