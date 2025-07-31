# README: Scope Troubleshooting Tool
This document serves as a comprehensive guide to the Scope application, a Python-based tool designed to streamline the process of analyzing log files and managing troubleshooting sessions for collaborative teams. It outlines the application's purpose, key features, and intended workflow.

# Mission
The primary mission of Scope is to assist users in quickly identifying, isolating, and documenting critical issues by "reducing the scope of data" from large, complex log files. By centralizing all relevant information into a single, cohesive source of truth, Scope aims to enhance team collaboration and accelerate the troubleshooting process.

# Key Features and Intended Workflow
The application's workflow is centered around individual troubleshooting sessions, each representing a dedicated investigation.

# 1. Main Menu
Upon launching Scope, you are presented with a simple main menu with two primary options:

  - Start Troubleshooting: Initiate a brand-new session by selecting log file(s) for analysis.

  - Continue Troubleshooting: Resume work on a previously saved session, or import a session shared by a teammate.

# 2. Starting a New Session
This is the initial phase of any new investigation.

- File Selection: You are prompted to select one or more log files (typically .log or .txt formats). You can select multiple files at once.

- Analyzing the log content for stack traces. This feedback loop ensures you are aware of the application's progress, which is especially useful when dealing with large files.

- Automatic File Aggregation: All selected log files are automatically copied to a dedicated logs subdirectory within a new, unique session folder. This saves the user a manual step and ensures all original log data is conveniently located in a single place.

- Initial Analysis: The application analyzes the aggregated log content to identify unique stack traces, counting their occurrences and assigning a weighted priority.

# 3. The Troubleshooting Dashboard
After the initial analysis, you are taken to the Troubleshooting Dashboard. This is your central workspace for managing the investigation. The interface is designed with a focus on data visibility and user-friendly interaction.

- Resizable Panes: The dashboard features a resizable layout, allowing you to adjust the size of three main panes:

  - The left pane lists all unique stack traces found during the analysis.

  - The top-right pane displays the full content of a selected stack trace.

  - The bottom pane is dedicated to notes and file management.

- Stack Trace List: The list on the left displays each unique stack trace. Each entry includes:

  - A numeric [weight] indicating its priority or severity.

  - The full exception name (e.g., io.trino.spi.TrinoException).

  - A count of its occurrences in the log files.

- Search Functionality: A search bar is available at the top of the dashboard. When you type in a term:

  - Matching text within the currently displayed stack trace is highlighted in yellow.

  - The corresponding stack trace button in the list on the left will also be highlighted in yellow, providing a quick visual cue of which traces contain your search term.

- Full Stack Trace Display: Clicking an entry in the list populates the top-right pane with the complete stack trace. You can adjust the font size to your preference using the "A+" and "A-" buttons, and a "Copy Trace" button allows you to quickly copy the entire trace to your clipboard.

- Notes Section: The bottom pane offers a powerful note-taking experience with live Markdown formatting.

- Live Markdown: The notes editor provides a live preview of basic Markdown syntax for headings (h1., h2.) and code blocks ({{code}}), helping you keep your notes organized.

- Escalation Template: The "Escalation Template" button inserts a standardized template into your notes. This template helps ensure all key pieces of information are captured for escalation purposes.

- Code Block and Trace Name Insertion: You can easily insert a Markdown code block or the name of the currently selected stack trace into your notes with dedicated buttons.

  - All notes are saved automatically as you type.

- File Management:

  - Copy Relevant Files: This button lets you select and copy any additional files (e.g., screenshots, configuration files) into the session's main directory.

  - Export Notes: Exports your notes into a JIRA-compatible Markdown (.md) file, complete with all formatting syntax.

  - Export Session: Compresses the entire session directory (including all log files, notes, and other relevant files) into a single .zip file for easy sharing with your team.

# 4. Collaborative Workflow
Scope is designed to support teamwork through its data management.

- Per-Session Storage: Each session and all its data are self-contained within a single directory on disk.

- Import/Export: A team member can export a session, zip it, and share the .zip file. Another user can then import this zip file from the "Continue Troubleshooting" screen. The application handles unpacking the archive, re-analyzing the log files to ensure data integrity with the user's local definitions, and makes the session available for continued work.

This structure ensures that all troubleshooting efforts are encapsulated, easily sharable, and consistently managed across a team.
