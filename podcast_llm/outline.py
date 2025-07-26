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


logger = logging.getLogger(__name__)


def format_wikipedia_document(doc):
    """
    Format a Wikipedia document for use in prompt context.

    Takes a Wikipedia document object and formats its metadata and content into a 
    structured string format suitable for inclusion in LLM prompts. The format
    includes a header with the article title followed by the full article content.

    Args:
        doc: Wikipedia document object containing metadata and page content

    Returns:
        str: Formatted string with article title and content
    """
    return f"### {doc.metadata['title']}\n\n{doc.page_content}"


def outline_episode(config: PodcastConfig, topic: str, background_info: list, episode_guidance: Optional[str] = None) -> PodcastOutline:
    """
    Generate a structured outline for a podcast episode.

    Takes a topic and background research information, then uses LangChain and GPT-4 
    to generate a detailed podcast outline with sections and subsections. The outline
    is structured using Pydantic models for type safety and validation.

    Args:
        topic (str): The main topic for the podcast episode
        background_info (list): List of Wikipedia document objects containing research material

    Returns:
        PodcastOutline: Structured outline object containing sections and subsections
    """
    logger.info(f'Generating outline for podcast on: {topic}')
    
    prompthub_path = "evandempsey/podcast_outline:6ceaa688"
    try:
        outline_prompt = hub.pull(prompthub_path)
        logger.info(f"Got prompt from hub: {prompthub_path}")
    except Exception as e:
        logger.warning(f"Failed to pull prompt from hub: {e}")
        # Fallback to local prompt with duration guidance
        from langchain_core.prompts import PromptTemplate
        outline_prompt = PromptTemplate(
            input_variables=["episode_structure", "topic", "context_documents", "episode_guidance"],
            template="""You are an expert podcast producer. Create a detailed outline for a podcast episode.

Episode Structure:
{episode_structure}

Topic: {topic}

Background Information:
{context_documents}

Episode Guidance:
{episode_guidance}

Create a structured outline with sections and subsections that follows the episode structure above."""
        )
        logger.info("Using fallback local prompt with duration guidance support")

    outline_llm = get_long_context_llm(config)
    outline_chain = outline_prompt | outline_llm.with_structured_output(
        PodcastOutline
    )

    # Prepare episode guidance for the prompt
    guidance_text = ""
    if episode_guidance and episode_guidance.strip():
        guidance_text = f"\n\nAdditional guidance for Main Discussion Topics:\n{episode_guidance.strip()}"
    
    prompt_vars = {
        "episode_structure": config.episode_structure_for_prompt,
        "topic": topic,
        "context_documents": "\n\n".join([format_wikipedia_document(d) for d in background_info]),
        "episode_guidance": guidance_text
    }
    
    outline = outline_chain.invoke(prompt_vars)

    logger.info(outline.as_str)
    return outline
