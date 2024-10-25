ERROR = "error"
WARNING = "warning"

MISSING_FILE = "missing_file"
UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
FILE_TOO_LARGE = "file_too_large"
UNSUPPORTED_ZIP = "unsupported_zip"
INVALID_ZIP = "invalid_zip"

MISSING_SHEET = "missing_sheet"
INVALID_HEADER = "invalid_header"
INVALID_HEADER_CELLS = "invalid_header_cells"
INVALID_FILE_LOAD = "invalid_file_load"
ASSESSMENT_ID_MISMATCH = "assessment_id_mismatch"
INVALID_SHEET = "invalid_sheet"
INVALID_QUESTIONS = "invalid_questions"
INVALID_CHOICES = "invalid_choices"
SURVEYANSWERLIKERTSERIALIZER = "invalid_answers"
ANSWER_SAVE = "answer_save"


def ingest_400(key, message, data=None):
    response_obj = {key: {"level": ERROR, "message": message}}
    if data:
        response_obj[key]["data"] = data
    return response_obj
