from copy import copy
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Alignment, DEFAULT_FONT, Protection
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.datavalidation import DataValidation
# from openpyxl.worksheet.protection import SheetProtection

from ..utils import unzip_file, strip_html
from ..utils.assessment import (
    attribute_scores,
    enforce_required_attributes,
    get_answer_by_slug,
    questionlikerts,
)

ERROR = "error"
WARNING = "warning"
# TODO: create elinordata.org subdomain for this s3 bucket
DOCUMENTATION_URL = "https://elinor-user-files.s3.amazonaws.com/dev/Document/2/Elinor_assessment_tool_protocol_v2022.1.pdf"
bold = copy(DEFAULT_FONT)
bold.bold = True
bold14pt = copy(DEFAULT_FONT)
bold14pt.bold = True
bold14pt.size = 14
wrapped_alignment = Alignment(
    horizontal="general",
    vertical="top",
    text_rotation=0,
    wrap_text=True,
    shrink_to_fit=True,
    indent=0,
)


class AssessmentXLSX:
    def __init__(self, assessment):
        self.assessment = assessment
        enforce_required_attributes(self.assessment)
        self._questions = []
        self.attribute_scores = attribute_scores(self.assessment)
        self.workbook = None
        self.xlsxfile = None
        self.validations = {}
        self.ws_def = {
            "survey": {
                "intro": {
                    "row": 1,
                    "header": [
                        {
                            "content": "Please make sure you read our protocol before answering this survey:",
                            "font": bold,
                        },
                        {},
                        {"content": DOCUMENTATION_URL, "hyperlink": DOCUMENTATION_URL},
                    ],
                },
                "columns": {
                    "row": 3,
                    "header": [
                        {"content": "Survey Question", "font": bold14pt, "width": 80},
                        {"content": "key", "hidden": True},
                        {"content": "Answer", "width": 40},
                        {"content": "Explanation", "width": 40},
                        {"content": "Rationale", "width": 20},
                        {"content": "Information", "width": 20},
                        {"content": "Guidance", "width": 20},
                    ],
                },
            },
            "choices": {
                "columns": {
                    "row": 1,
                    "header": [
                        {"content": "key"},
                        {"content": "excellent_3"},
                        {"content": "good_2"},
                        {"content": "average_1"},
                        {"content": "poor_0"},
                    ],
                }
            },
        }

    @property
    def sheetnames(self):
        return list(self.ws_def.keys())

    @property
    def questions(self):
        if not self._questions:
            qs = questionlikerts()
            _choices_header = self.ws_def[self.sheetnames[1]]["columns"]["header"]
            for q in qs:
                question = copy(q)
                question.choices = []
                for col in _choices_header[1:]:
                    attr = col.get("content")
                    val = getattr(q, attr)
                    choice = attr.split("_")[1]
                    question.choices.append(f"{choice}: {strip_html(val)}")
                self._questions.append(question)
        return self._questions

    def write_header(self, sheetname, section="columns"):
        _header_row = self.ws_def[sheetname][section]["row"]
        _header = self.ws_def[sheetname][section]["header"]
        ws = self.workbook.get_sheet_by_name(sheetname)

        for i, col in enumerate(_header):
            _cell = ws.cell(row=_header_row, column=i + 1, value=col.get("content"))
            col_index = get_column_letter(i + 1)
            _font = col.get("font")
            _link = col.get("hyperlink")
            _hidden = col.get("hidden")
            _width = col.get("width")
            if _font:
                _cell.font = _font
            if _link:
                _cell.hyperlink = _link
            if _hidden:
                ws.column_dimensions[col_index].hidden = True
            if _width:
                ws.column_dimensions[col_index].width = _width

    def add_survey_validation(self, qkey):
        ws_survey = self.workbook.get_sheet_by_name(self.sheetnames[0])
        ws_choices = self.workbook.get_sheet_by_name(self.sheetnames[1])
        val_formula = ""
        # Could use question.choices but doesn't work if a choice has a comma
        for i, row in enumerate(ws_choices.iter_rows()):
            key = row[0].value
            if key == qkey:
                val_formula = f"{self.sheetnames[1]}!$B${i + 1}:$E${i + 1}"
        validation = DataValidation(
            type="list",
            allow_blank=True,
            formula1=val_formula,
            showErrorMessage=True,
            errorTitle="invalid choice",
            error="Please select a choice from the list",
        )
        ws_survey.add_data_validation(validation)
        return validation

    def protect_sheet(self, ws, exception_columns=None):
        # ws_choices.protection = SheetProtection(formatColumns=False, formatRows=False, formatCells=False)
        # TODO: setting formatColumns/formatRows = False has no effect (at least in LibreOffice).
        ws.protection.sheet = True
        ws.protection.formatColumns = False
        ws.protection.formatRows = False
        for col in exception_columns or []:
            for cell in ws[col]:
                cell.protection = Protection(locked=False)

    def get_choice_by_answer(self, question, choice):
        for question_choice in question.choices:
            val = int(question_choice.split(": ")[0])
            if choice == val:
                return question_choice
        return ""

    def generate_from_assessment(self):
        self.workbook = Workbook(iso_dates=True)
        self.workbook.worksheets[0].title = self.sheetnames[0]
        self.workbook.create_sheet(self.sheetnames[1])
        ws_survey = self.workbook.get_sheet_by_name(self.sheetnames[0])
        ws_choices = self.workbook.get_sheet_by_name(self.sheetnames[1])

        self.write_header(self.sheetnames[0], section="intro")
        self.write_header(self.sheetnames[0])
        self.write_header(self.sheetnames[1])
        for q in self.questions:
            choices = [q.key] + [c for c in q.choices]
            ws_choices.append(choices)

        arow = self.ws_def[self.sheetnames[0]]["columns"]["row"] + 1
        for attribute in self.assessment.attributes.order_by("order", "name"):
            attr_cell = ws_survey.cell(row=arow, column=1, value=attribute.name.upper())
            attr_cell.font = bold
            attr_cell.alignment = wrapped_alignment
            arow += 1
            for question in self.questions:
                if question.attribute == attribute:
                    qtext = f"{question.number}. {question.text}"
                    answer = (
                        get_answer_by_slug(self.attribute_scores, question.key) or {}
                    )
                    choice = answer.get("choice", "")
                    choice_text = self.get_choice_by_answer(question, choice)
                    validation = self.add_survey_validation(question.key)
                    explanation = answer.get("explanation", "")
                    rationale = strip_html(question.rationale)
                    information = strip_html(question.information)
                    guidance = strip_html(question.guidance)

                    ws_survey.row_dimensions[arow].height = 32
                    qrow = [
                        qtext,
                        question.key,
                        choice_text,
                        explanation,
                        rationale,
                        information,
                        guidance,
                    ]
                    for i, val in enumerate(qrow):
                        _cell = ws_survey.cell(row=arow, column=i + 1, value=val)
                        if i == 0:
                            _cell.alignment = wrapped_alignment
                        if i == 2:
                            validation.add(_cell)

                    arow += 1

        self.protect_sheet(ws_choices)
        self.protect_sheet(ws_survey, ["C", "D"])

    def load_from_file(self, file):
        try:
            self.workbook = load_workbook(file, read_only=True)
        except InvalidFileException as e:
            self.validations["invalid_file_load"] = {"level": ERROR, "message": str(e)}

        # validate file structure against ws_def; populate self.validations to be passed back as 400s
        # populate self.answers
        # then, self.ingest(dryrun); use serializers to save and return as appropriate

        # Extract worksheet names, column names, and static content
        # for sheet in self.workbook.sheetnames:
        #     self.worksheet_names.append(sheet)
        #     self.column_names[sheet] = [col.value for col in self.workbook[sheet][1]]
        #     self.static_content[sheet] = [row for row in self.workbook[sheet].iter_rows(min_row=2, values_only=True)]
