# CLAUDE and GEMINI

This file provides guidance to AI assistants when working with code in this repository.

## Project Overview

This project aims to help government agents decide public policies based in information about cities. It comprises of the most extensible database about cities in Brazil, including info about electoral data, demographic and economics. It will have authentication features that limit an government agent to see info about regions not in his scope. Security is a first attention in this project. In the last step, it will feature an chatbot capable of resuming data for high executives, like 'Show all cities with more than 20,000 citizens that has an mayor from the Workers Party' or 'Show me the total of cities that has an evaluation superior to 3'.

## Development Commands

### Setup
```bash
# TODO: Add installation/setup commands
```

### Build
```bash
# TODO: Add build commands
```

### Testing
```bash
# TODO: Add test commands
# TODO: Add command to run a single test
```

### Linting
```bash
# TODO: Add linting commands
```

## Architecture

It will be a Django-based architecture, with monolith frontend. User granular permission system will be obtained through Django Admin, by expanding it. The development will be through a containerized environment


## Key Directories
* App will be kept in ./app folder
* All django module apps will be kept inside a module called /apps, for organization purpose.

## Important Notes

[TODO: Add any project-specific conventions, gotchas, or important context that requires reading multiple files to understand]
