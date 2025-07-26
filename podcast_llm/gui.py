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

import gradio as gr
from gradio_log import Log

from .config.logging_config import setup_logging
from .generate import generate
from .utils.checkpointer import to_snake_case

PACKAGE_ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = os.path.join(PACKAGE_ROOT, 'config', 'config.yaml')

temp_log_file = tempfile.NamedTemporaryFile(mode='w', delete=False).name


def submit_handler(
    topic: str,
    mode_of_operation: str,
    source_files: list[str],
    source_urls: str,
    qa_rounds: int,
    use_checkpoints: bool,
    custom_config_file: str | None,
    episode_guidance: str,
    duration_target: int,
    text_output: str,
    audio_output: str
) -> None:
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
        None
    """
    setup_logging(log_level=logging.INFO, output_file=temp_log_file)
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

    # Ensure text output has .md extension
    if text_output.strip():
        text_output_file = text_output.strip()
        if not text_output_file.endswith('.md'):
            text_output_file += '.md'
    else:
        # Use topic as filename if text output is empty
        text_output_file = f"{to_snake_case(topic)}.md"
    
    # Ensure audio output has .mp3 extension
    if audio_output.strip():
        audio_output_file = audio_output.strip()
        if not audio_output_file.endswith('.mp3'):
            audio_output_file += '.mp3'
    else:
        # Use topic as filename if audio output is empty
        audio_output_file = f"{to_snake_case(topic)}.mp3"

    # Split URLs by line and filter out non-URL lines
    source_urls_list = [
        url.strip() 
        for url in source_urls.strip().split('\n') 
        if url.strip().startswith(('http://', 'https://'))
    ]

    # Combine source files and URLs into single sources list
    sources = (source_files or []) + source_urls_list
    sources = sources if sources else None

    # Adjust Q&A rounds based on duration target
    adjusted_qa_rounds = qa_rounds
    if duration_target >= 20:
        # For very long podcasts, increase Q&A rounds significantly
        adjusted_qa_rounds = min(qa_rounds + 3, 10)
    elif duration_target >= 15:
        # For longer podcasts, increase Q&A rounds
        adjusted_qa_rounds = min(qa_rounds + 2, 10)
    elif duration_target <= 5:
        # For very short podcasts, decrease Q&A rounds significantly
        adjusted_qa_rounds = max(qa_rounds - 2, 1)
    elif duration_target <= 8:
        # For shorter podcasts, decrease Q&A rounds
        adjusted_qa_rounds = max(qa_rounds - 1, 1)
    
    if adjusted_qa_rounds != qa_rounds:
        logging.info(f"Adjusted Q&A rounds from {qa_rounds} to {adjusted_qa_rounds} for {duration_target}-minute target")
    
    generate(
        topic=topic.strip(),
        mode=mode_of_operation,
        sources=sources,
        qa_rounds=adjusted_qa_rounds,
        use_checkpoints=use_checkpoints,
        audio_output=audio_output_file,
        text_output=text_output_file,
        episode_guidance=episode_guidance.strip() if episode_guidance.strip() else None,
        duration_target=duration_target,
        config=custom_config_file if custom_config_file else DEFAULT_CONFIG_PATH,
        debug=False,
        log_file=temp_log_file
    )

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

        # Conversation Options Section
        gr.Markdown('## Conversation Options')
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
            duration_target_input = gr.Number(
                label='Target Duration (minutes)',
                value=10,
                interactive=True,
                minimum=5,
                maximum=60,
                precision=0
            )
        
        # Episode Structure Guidance (Collapsible)
        with gr.Accordion("Episode Structure Guidance", open=False):
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

        # Behavior Options Section
        gr.Markdown('## Behaviour Options')
        use_checkpoints_input = gr.Checkbox(
            label='Use Checkpoints',
            value=True
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
                label='Text output (.md)', 
                placeholder='Leave empty to use topic name'
            )
            audio_output_input = gr.Textbox(
                label='Audio output (.mp3)', 
                placeholder='Leave empty to use topic name'
            )
        gr.Markdown('*Leave output fields empty to automatically use the topic name as filename*')

        # Submit Button
        submit_button = gr.Button('Generate Podcast')
        submit_button.click(
            fn=submit_handler,
            inputs=[
                topic_input,
                mode_of_operation,
                source_files,
                source_urls,
                qa_rounds_input,
                use_checkpoints_input,
                custom_config_file_input,
                episode_guidance_input,
                duration_target_input,
                text_output_input,
                audio_output_input
            ],
            outputs=[]
        )

        # Log Display
        gr.Markdown('## System Log')
        with gr.Row():
            Log(temp_log_file, dark=True, xterm_font_size=12, height=400)
        
        # Add spacing to prevent footer overlap
        gr.Markdown('<div style="height: 100px;"></div>')

    iface.launch(inbrowser=True)


if __name__ == '__main__':
    main()
