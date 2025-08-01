"""
Podcast generation module.

This module provides functionality to generate complete podcast episodes from a given topic.
It can operate in two modes:
1. Research mode: Automatically researches the topic online
2. Existing context mode: Uses provided URLs and files as source material

Example:
    Research mode:
    >>> generate(topic='Artificial Intelligence', mode='research')

    Existing context mode:
    >>> generate(
    ...     topic='Artificial Intelligence',
    ...     mode='context',
    ...     sources=['article.pdf', 'https://example.com/ai-article']
    ... )
"""

import os
import argparse
from pathlib import Path
from typing import Optional, List, Literal, Generator
from podcast_llm.config import PodcastConfig, setup_logging
from podcast_llm.utils.checkpointer import (
    Checkpointer,
    to_snake_case
)
from podcast_llm.text_to_speech import generate_audio
from podcast_llm.utils.text import generate_markdown_script
from podcast_llm.extractors import extract_content_from_sources
from podcast_llm.research import research_background_info, research_discussion_topics, summarize_research_material
from podcast_llm.outline import outline_episode
from podcast_llm.writer import write_draft_script, write_final_script
import logging

logger = logging.getLogger(__name__)

PACKAGE_ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = os.path.join(PACKAGE_ROOT, 'config', 'config.yaml')


def generate(
    topic: str,
    mode: Literal['research', 'context'],
    sources: Optional[List[str]] = None,
    qa_rounds: int = 2,
    use_checkpoints: bool = True,
    audio_output: Optional[str] = None,
    text_output: Optional[str] = None,
    episode_guidance: Optional[str] = None,
    config: str = DEFAULT_CONFIG_PATH,
    debug: bool = False,
    log_file: Optional[str] = None,
    summarization_enabled: bool = True,
    key_topics_count: str = "3-5",
    target_duration: Optional[int] = None,
) -> Generator[str, None, None]:
    """
    Generate a podcast episode, yielding progress updates.
    
    Args:
        topic: Topic of the podcast
        mode: Generation mode - either 'research' or 'context'
        sources: List of URLs and file paths to use as source material (for context mode)
        qa_rounds: Number of Q&A rounds
        use_checkpoints: Whether to use checkpointing
        audio_output: Path to save audio output
        text_output: Path to save text output
        config: Path to config file
        debug: Whether to enable debug logging
        log_file: Log output file
        summarization_enabled: Whether to enable summarization
        key_topics_count: Number of key topics to focus on
        target_duration: Target duration in minutes for the entire podcast
    """
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(log_level, output_file=log_file)
    
    config = PodcastConfig.load(yaml_path=config)

    checkpointer = Checkpointer(
        checkpoint_key=f"{to_snake_case(topic)}_qa_{qa_rounds}_",
        enabled=use_checkpoints
    )

    # Get background info based on mode
    if mode == 'research':
        yield "Researching background information..."
        background_info = checkpointer.checkpoint(
            research_background_info,
            [config, topic],
            stage_name='background_info'
        )
    else:  # context mode
        yield "Extracting content from sources..."
        if not sources:
            raise ValueError("Sources must be provided when using context mode")
        background_info = checkpointer.checkpoint(
            extract_content_from_sources,
            [sources],
            stage_name='background_info'
        )

    # Summarize background information if enabled
    if summarization_enabled:
        yield "Summarizing research material..."
        background_info = checkpointer.checkpoint(
            summarize_research_material,
            [config, topic, background_info, key_topics_count],
            stage_name='summarized_info'
        )

        # Save summarized research for debugging
        summary_output_path = checkpointer.checkpoint_dir / f"{checkpointer.checkpoint_key}_summarized_research.md"
        with open(summary_output_path, "w") as f:
            f.write(f"# Summarized Research for Topic: {topic}\n\n")
            for i, doc in enumerate(background_info):
                f.write(f"## Summary of Source {i+1}\n")
                f.write(f"**Original Title:** {doc.metadata.get('original_title', 'N/A')}\n")
                f.write(f"**Source:** {doc.metadata.get('source', 'N/A')}\n\n")
                f.write(f"{doc.page_content}\n\n")
                f.write("---\n\n")

    yield "Generating outline..."
    outline = checkpointer.checkpoint(
        outline_episode,
        [config, topic, background_info, episode_guidance, key_topics_count, target_duration],
        stage_name='outline'
    )

    # Get detailed info based on mode
    if mode == 'research':
        yield "Researching discussion topics..."
        deep_info = checkpointer.checkpoint(
            research_discussion_topics,
            [config, topic, outline],
            stage_name='deep_info'
        )
    else:
        deep_info = background_info

    yield "Writing draft script..."
    draft_script = checkpointer.checkpoint(
        write_draft_script,
        [config, topic, outline, background_info, deep_info, qa_rounds],
        stage_name='draft_script'
    )
    
    yield "Writing final script..."
    final_script = checkpointer.checkpoint(
        write_final_script,
        [config, topic, draft_script],
        stage_name='final_script'
    )

    if text_output:
        with open(text_output, 'w+') as f:
            f.write(generate_markdown_script(topic, outline, final_script))

    if audio_output:
        generate_audio(config, final_script, audio_output)

    yield "Done!"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate podcasts using LLMs and TTS'
    )
    parser.add_argument(
        'topic',
        help='Topic of the podcast'
    )
    parser.add_argument(
        '--mode',
        choices=['research', 'context'],
        default='research',
        help='Generation mode: research (automatic research) or context (use provided sources)'
    )
    parser.add_argument(
        '--sources',
        nargs='+',
        help='List of URLs and file paths to use as source material (required for context mode)'
    )
    parser.add_argument(
        '--qa-rounds',
        type=int,
        default=2,
        help='Number of question-answer rounds per section'
    )
    parser.add_argument(
        '--checkpoint',
        action='store_true',
        dest='checkpoint',
        default=True,
        help='Enable checkpointing (default: True)'
    )
    parser.add_argument(
        '--no-checkpoint',
        action='store_false',
        dest='checkpoint',
        help='Disable checkpointing'
    )
    parser.add_argument(
        '--audio-output',
        type=str,
        default=None,
        help='Output filename for the generated audio'
    )
    parser.add_argument(
        '--text-output',
        type=str,
        default=None,
        help='Output filename for the generated text script'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help='Path to YAML config file'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_arguments()
    
    if args.mode == 'context' and not args.sources:
        raise ValueError("--sources must be provided when using context mode")
        
    for update in generate(
        topic=args.topic,
        mode=args.mode,
        sources=args.sources,
        qa_rounds=args.qa_rounds,
        use_checkpoints=args.checkpoint,
        audio_output=args.audio_output,
        text_output=args.text_output,
        config=args.config,
        debug=args.debug
    ):
        print(update)


if __name__ == '__main__':
    main()
