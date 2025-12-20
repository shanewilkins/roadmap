# Next steps for Shane based on recent code edits

## Goal: freeze the api
- refactor anything that smells funny in the radon CC report
- refactor the UX
- we have to refactor all the tests too to match our new architecture
- then we need to update all existing tests to tests the functionality in the new location.
- then we can kill all the dummy files that are just placeholders for backwards compatibility -- copilot should have marked all those.
- then we need an extensive hunt for DRY violations and fix those too.
- finally, we need a final review of all of our architecture to make sure that everything is in the right place.
-formatters.py isn't keeping with separation of presentation and formatting logic. calls rich. also frankly too long

## goal: improve error handling, logging, observability
- we need to make sure all the logging decorators are used in all cli commands
- we need to make sure all the error handling decorators are used in all cli commands
- we need to make sure all the performance tracking decorators are used in all cli commands
- we need to make sure all the validation logic is using the field validators and not rolling their own error messages
- we need to make sure all the error messages are consistent and informative

## goal: improve documentation
- we need to make sure all the docstrings are present and accurate
- we need to make sure all the modules have module-level docstrings
- we need to make sure all the functions have function-level docstrings
- we need to make sure all the classes have class-level docstrings
- we need to make sure all the public APIs are documented in the docs folder
- we need to make sure all the examples in the docs folder are up to date with the current API
- we need to make sure all the architecture diagrams are up to date with the current architecture
