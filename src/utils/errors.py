"""Error hierarchy. Every error carries a `user_message` that is safe to show in the UI."""
from __future__ import annotations


class VisitIQError(Exception):
    """Base error with a friendly message for the user."""

    default_message = "Something went wrong. Please try again."

    def __init__(self, user_message: str | None = None, *, detail: str | None = None):
        self.user_message = user_message or self.default_message
        self.detail = detail
        super().__init__(detail or self.user_message)


class FileValidationError(VisitIQError):
    default_message = "The file could not be accepted."


class UnsupportedFileTypeError(FileValidationError):
    default_message = "This file type is not supported. Please upload PDF, TXT, CSV or XLSX."


class FileTooLargeError(FileValidationError):
    default_message = "The file is too large."


class EmptyFileError(FileValidationError):
    default_message = "The file is empty."


class CorruptFileError(FileValidationError):
    default_message = "The file appears to be damaged or is not what its extension says."


class IrrelevantDocumentError(FileValidationError):
    default_message = "This document does not look like Hyderabad travel or tourism content."


class LLMUnavailableError(VisitIQError):
    default_message = "The language model is unavailable right now; showing a rule-based answer instead."


class VectorStoreError(VisitIQError):
    default_message = "The knowledge base could not be read. Try 'Reset knowledge base' and reload the documents."
