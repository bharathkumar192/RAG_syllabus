from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class SyllabusUploadForm(FlaskForm):
    title = StringField('Course Title', 
                       validators=[DataRequired(), Length(min=2, max=200)])
    department = StringField('Department',
                           validators=[DataRequired(), Length(min=2, max=100)])
    course_number = StringField('Course Number',
                              validators=[DataRequired(), Length(min=2, max=20)])
    syllabus_file = FileField('Syllabus PDF',
                             validators=[
                                 FileRequired(),
                                 FileAllowed(['pdf'], 'PDF files only!')
                             ])
    submit = SubmitField('Upload Syllabus')