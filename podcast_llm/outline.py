"""
Podcast outline generation module.

This module provides functionality for generating and structuring podcast outlines.
It contains utilities for formatting and manipulating outline structures, as well as
functions for generating complete podcast outlines from topics and research material.

The module leverages LangChain and GPT-4 to intelligently structure podcast content
into a hierarchical outline format. It uses prompts from the LangChain Hub to ensure
consistent and high-quality outline generation.

Functions:
    format_wikipedia_document: Formats Wikipedia content for use in prompts
    outline_episode: Generates a complete podcast outline from a topic and research

Example:
    outline = outline_episode(
        config=podcast_config,
        topic="Artificial Intelligence",
        background_info=research_docs
    )
    print(outline.as_str)
"""


import logging
from typing import Optional
from langchain import hub
from podcast_llm.config import PodcastConfig
from podcast_llm.utils.llm import get_long_context_llm
from podcast_llm.models import (
    PodcastOutline
)
from langchain_core.prompts import PromptTemplate


logger = logging.getLogger(__name__)


def format_document_for_prompt(doc):
    """
    Format a document for use in prompt context.

    Takes a document object and formats its metadata and content into a
    structured string format suitable for inclusion in LLM prompts. The format
    includes a header with the article title followed by the full article content.

    Args:
        doc: A Document object containing metadata and page content

    Returns:
        str: Formatted string with article title and content
    """
    title = doc.metadata.get('title') or doc.metadata.get('original_title', 'Untitled Document')
    return f"### {title}\n\n{doc.page_content}"


def outline_episode(config: PodcastConfig, topic: str, background_info: list, episode_guidance: Optional[str] = None, key_topics_count: str = "3-5", target_duration: Optional[int] = None) -> PodcastOutline:
    """
    Generate a structured outline for a podcast episode.

    Takes a topic and background research information, then uses LangChain and GPT-4
    to generate a detailed podcast outline with sections and subsections. The outline
    is structured using Pydantic models for type safety and validation.

    Args:
        topic (str): The main topic for the podcast episode
        background_info (list): List of Wikipedia document objects containing research material
        episode_guidance (Optional[str]): Custom guidance for the episode
        key_topics_count (str): Number of key topics to focus on
        target_duration (Optional[int]): Target duration in minutes for the entire podcast

    Returns:
        PodcastOutline: Structured outline object containing sections and subsections
    """
    logger.info(f'Generating outline for podcast on: {topic}')
    
    # Calculate word count based on target duration
    if target_duration:
        # Estimate: 150 words per minute for conversational speech
        target_words = target_duration * 150
        logger.info(f"Target duration: {target_duration} minutes, Target words: {target_words}")
    else:
        target_words = None
    
    # This prompt is not from the hub, it's defined locally.
    outline_prompt_template = """
    You are an expert podcast producer. Your task is to create a podcast outline about '{topic}'.
    
    Based on the provided research, identify the '{key_topics_count}' most critical and engaging main discussion topics.
    DO NOT generate more than the requested number of main topics.
    For each main topic, create 2-3 concise and relevant sub-sections.

    {duration_constraint}

    Here is the general structure to follow:
    {episode_structure}

    Here is the summarized research material:
    {context_documents}
    
    Additional Guidance:
    {episode_guidance}

    Create the outline now.
    """
    outline_prompt = PromptTemplate.from_template(outline_prompt_template)
    logger.info("Using local outline prompt to enforce topic count.")

    outline_llm = get_long_context_llm(config)
    outline_chain = outline_prompt | outline_llm.with_structured_output(
        PodcastOutline
    )

    # Prepare episode guidance for the prompt
    guidance_text = ""
    if episode_guidance and episode_guidance.strip():
        guidance_text = f"\n\nAdditional guidance for Main Discussion Topics:\n{episode_guidance.strip()}"

    # Prepare duration constraint
    duration_constraint = ""
    if target_duration:
        duration_constraint = f"""
CRITICAL LENGTH REQUIREMENT:
- This outline must result in a {target_duration}-minute podcast (approximately {target_words} words)
- Keep all content concise and focused
- Avoid overly detailed explanations or multiple examples
- Each subsection should be designed for brief, impactful discussion
- Focus only on the most essential points that can be covered in {target_duration} minutes
"""

    prompt_vars = {
        "episode_structure": config.episode_structure_for_prompt,
        "topic": topic,
        "context_documents": "\n\n".join([format_document_for_prompt(d) for d in background_info]),
        "episode_guidance": guidance_text,
        "key_topics_count": key_topics_count,
        "duration_constraint": duration_constraint,
    }
    
    outline = outline_chain.invoke(prompt_vars)

    logger.info(outline.as_str)
    return outline
