"""
Graphical user interface module for podcast generation.

This module provides a web-based GUI using Gradio for generating podcasts. It allows users
to interactively specify podcast generation parameters including:

- Topic selection
- Operation mode (research or context-based)
- Source materials (files and URLs) for context mode
- Number of Q&A rounds
- Checkpointing preferences
- Custom configuration
- Output paths for text and audio

The GUI provides a user-friendly way to access the podcast generation functionality
without needing to use the command line interface.

The module handles form submission, input validation, logging setup, and coordinates
with the core generation functionality. It uses temporary files for logging and
provides real-time feedback during the generation process.
"""


import logging
import os
from pathlib import Path
import tempfile
from typing import Generator, Optional, List

import gradio as gr
from gradio_log import Log

from .config.logging_config import setup_logging
from .generate import generate, DEFAULT_CONFIG_PATH
from .utils.checkpointer import to_snake_case

PACKAGE_ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = os.path.join(PACKAGE_ROOT, 'config', 'config.yaml')

# Create a temporary log file for this run
temp_log_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".log").name


def submit_handler(
    topic: str,
    mode_of_operation: str,
    source_files: list[str],
    source_urls: str,
    qa_rounds: int,
    use_checkpoints: bool,
    generate_audio: bool,
    episode_guidance: str,
    custom_config_file: str | None,
    text_output: str,
    audio_output: str,
    summarization_enabled: bool,
    key_topics_count: str,
    target_duration: int,
) -> Generator[str, None, None]:
    """
    Handle form submission for podcast generation.

    Processes user inputs from the GUI form and calls the generate function with appropriate parameters.
    Handles input validation, logging, and file path processing.

    Args:
        topic: The podcast topic
        mode_of_operation: Either 'research' or 'context' mode
        source_files: List of source file paths to use as context
        source_urls: Newline-separated string of URLs to use as context
        qa_rounds: Number of Q&A rounds per section
        use_checkpoints: Whether to enable checkpointing
        custom_config_file: Optional path to custom config file
        text_output: Path to save text output (optional)
        audio_output: Path to save audio output (optional)

    Returns:
        Generator[str, None, None]: A generator yielding progress updates.
    """
    # Define the log file name for this specific run
    run_log_file = f"run_{to_snake_case(topic)}.log"

    # Clear the log file by opening in write mode, which truncates it
    with open(run_log_file, 'w') as f:
        pass  # Just opening in 'w' mode is enough to clear it

    # Set up logging
    log_level = logging.INFO
    setup_logging(log_level=logging.INFO, output_file=run_log_file)

    # Print values and types of all arguments
    logging.info(f'Topic: {topic} (type: {type(topic)})')
    logging.info(f'Mode of Operation: {mode_of_operation} (type: {type(mode_of_operation)})')
    logging.info(f'Source Files: {source_files} (type: {type(source_files)})')
    logging.info(f'Source URLs: {source_urls} (type: {type(source_urls)})')
    logging.info(f'QA Rounds: {qa_rounds} (type: {type(qa_rounds)})')
    logging.info(f'Use Checkpoints: {use_checkpoints} (type: {type(use_checkpoints)})')
    logging.info(f'Custom Config File: {custom_config_file} (type: {type(custom_config_file)})')
    logging.info(f'Text Output: {text_output} (type: {type(text_output)})')
    logging.info(f'Audio Output: {audio_output} (type: {type(audio_output)})')
    logging.info(f'Target Duration: {target_duration} (type: {type(target_duration)})')

    # Load config to get output directory
    from podcast_llm.config import PodcastConfig
    config = PodcastConfig.load(custom_config_file if custom_config_file else DEFAULT_CONFIG_PATH)

    # Ensure output directory exists
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure text output has .md extension and is in output directory
    if text_output.strip():
        text_output_file = text_output.strip()
        if not text_output_file.endswith('.md'):
            text_output_file += '.md'
        text_output_file = str(output_dir / text_output_file)
    else:
        text_output_file = str(output_dir / f"{to_snake_case(topic)}.md")

    # Ensure audio output has .mp3 extension and is in output directory
    if audio_output.strip():
        audio_output_file = audio_output.strip()
        if not audio_output_file.endswith('.mp3'):
            audio_output_file += '.mp3'
        audio_output_file = str(output_dir / audio_output_file)
    else:
        audio_output_file = str(output_dir / f"{to_snake_case(topic)}.mp3")


    # Split URLs by line and filter out non-URL lines
    source_urls_list = [
        url.strip()
        for url in source_urls.strip().split('\n')
        if url.strip().startswith(('http://', 'https://'))
    ]

    # Combine source files and URLs into single sources list
    sources = (source_files or []) + source_urls_list
    sources = sources if sources else None

    # Set qa_rounds directly
    adjusted_qa_rounds = qa_rounds

    if adjusted_qa_rounds != qa_rounds:
        logging.info(f"Q&A rounds set to {adjusted_qa_rounds}")

    final_audio_output = audio_output_file if generate_audio else None

    # Use a for loop to yield progress from the generator
    for progress_update in generate(
        topic=topic.strip(),
        mode=mode_of_operation,
        sources=sources,
        qa_rounds=adjusted_qa_rounds,
        use_checkpoints=use_checkpoints,
        audio_output=final_audio_output,
        text_output=text_output_file,
        episode_guidance=episode_guidance.strip() if episode_guidance.strip() else None,
        config=custom_config_file if custom_config_file else DEFAULT_CONFIG_PATH,
        debug=False,
        log_file=run_log_file,
        summarization_enabled=summarization_enabled,
        key_topics_count=key_topics_count,
        target_duration=target_duration,
    ):
        yield progress_update


def main():
    """
    Main entry point for the Gradio web interface.

    Creates and launches a Gradio interface that provides a user-friendly way to interact
    with the podcast generation system. The interface includes:
    - Topic input and conversation settings
    - Mode selection (research vs context)
    - Source file and URL inputs for context mode
    - Behavior options like checkpointing
    - Output configuration options

    The interface is organized into logical sections with clear labels and tooltips.
    All inputs are validated and passed to the generate() function.

    Returns:
        None
    """
    with gr.Blocks() as iface:
        # Title
        gr.Markdown('# Podcast-LLM', elem_classes='text-center')
        gr.Markdown('Generate a podcast from a topic or existing content')

        # Main Inputs Section
        with gr.Row():
            topic_input = gr.Textbox(label='Topic')
            qa_rounds_input = gr.Number(
                label='Number of rounds of Q&A per section',
                value=1,
                interactive=True,
                minimum=1,
                maximum=10,
                precision=0
            )

        # Summarization Controls
        with gr.Accordion("Summarization and Topic Focus", open=False):
            with gr.Row():
                summarization_enabled_input = gr.Checkbox(
                    label="Enable Summarization",
                    value=False,
                    info="Summarize source material to focus on key topics. Recommended for large sources."
                )
                key_topics_count_input = gr.Radio(
                    choices=["1-3", "3-5", "5+"],
                    label="Number of Key Topics",
                    value="3-5",
                    info="Guide the LLM to focus on this many main topics in the outline."
                )

        # Duration Control
        with gr.Accordion("Duration Control", open=True):
            with gr.Row():
                target_duration_input = gr.Number(
                    label="Target Duration (minutes)",
                    value=5,
                    minimum=1,
                    maximum=60,
                    step=1,
                    info="Target length for the entire podcast. This will guide the outline generation."
                )

        # Custom Episode Guidance Section
        with gr.Accordion("Custom Episode Guidance", open=False):
            episode_guidance_input = gr.TextArea(
                label='Custom Discussion Points',
                placeholder='Enter bullet points to guide the episode structure...\nExample:\n• Focus on practical applications\n• Include real-world examples\n• Address common challenges',
                info='These points will be added as subsections under "Main Discussion Topics"',
                lines=5
            )

        # Mode Selection Section
        gr.Markdown('## Mode of Operation')
        mode_of_operation = gr.Radio(
            choices=['research', 'context'],
            label='Mode',
            value='research',
            interactive=True,
            show_label=False
        )

        # Source Inputs Section
        with gr.Row(equal_height=True):
            source_files = gr.File(
                label='Source files',
                file_count='multiple',
                type='filepath'
            )
            source_urls = gr.TextArea(label='Source URLs')

        source_files.upload(
            lambda: "context",
            outputs=mode_of_operation
        )

        # Behavior Options Section
        gr.Markdown('## Behaviour Options')
        with gr.Row():
            use_checkpoints_input = gr.Checkbox(
                label='Use Checkpoints',
                value=True
            )
            generate_audio_input = gr.Checkbox(
                label='Generate Audio',
                value=True,
                info="Uncheck to generate script only"
            )

        # Advanced Options (Collapsible)
        with gr.Accordion("Advanced Options", open=False):
            gr.Markdown("Upload a custom YAML config to override default settings")
            custom_config_file_input = gr.File(
                label='Custom Config File (Optional)',
                type='filepath'
            )

        # Output Options Section
        gr.Markdown('## Output Options')
        with gr.Row():
            text_output_input = gr.Textbox(
                label='Text output (.md) - will be saved to /output/',
                placeholder='Leave empty to use topic name'
            )
            audio_output_input = gr.Textbox(
                label='Audio output (.mp3) - will be saved to /output/',
                placeholder='Leave empty to use topic name'
            )
        gr.Markdown('*Leave output fields empty to automatically use the topic name as filename in the /output/ directory*')

        # Submit Button
        with gr.Row():
            submit_button = gr.Button('Generate Podcast')
            stop_button = gr.Button('Stop Processing', variant='stop')

        status_output = gr.Textbox(label="Status", interactive=False)

        # Log Display
        gr.Markdown('## System Log')
        with gr.Row():
            log_display = Log(run_log_file, dark=True, xterm_font_size=12, height=400) # Ensure this watches the correct file

        # Add spacing to prevent footer overlap
        gr.Markdown('<div style="height: 100px;"></div>')

        click_event = submit_button.click(
            fn=submit_handler,
            inputs=[
                topic_input,
                mode_of_operation,
                source_files,
                source_urls,
                qa_rounds_input,
                use_checkpoints_input,
                generate_audio_input,
                episode_guidance_input,
                custom_config_file_input,
                text_output_input,
                audio_output_input,
                summarization_enabled_input,
                key_topics_count_input,
                target_duration_input,
            ],
            outputs=[status_output, log_display],
            queue=True
        )

        stop_button.click(fn=None, inputs=None, outputs=None, cancels=[click_event])

    iface.launch(inbrowser=True)


if __name__ == '__main__':
    main()
