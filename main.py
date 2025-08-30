import json
import os
from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory
from google import genai
from dotenv import load_dotenv
load_dotenv()
#TODO
#csv formatter
#batch divider
API_KEY = "AIzaSyAcKUmOQUpeC0DR9sqi90z2r0UdtKvxKbk"
client = genai.Client(api_key=API_KEY)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template_string(open("ui.html").read())

@app.route('/submit_json', methods=['POST'])
def submit_json():
    data = request.get_json()
    if not data:
        return "No JSON received", 400

    file_path = os.path.join(UPLOAD_FOLDER, "timetable_input.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

    prompt = f"""
You are an AI assistant that generates conflict-free academic timetables.
Here is the input data:
{json.dumps(data, indent=2)}

Please generate a timetable for the semester, assigning:
- each subject to rooms
- each subject to faculty
- time slots per working day
- ensuring no faculty, room, or student conflicts
- DONT START IT WITH "```json" or end it with "```"
- If it's not possible, tell me the problem and say invalid arrangement in the format "Invalid arrangement: <reason>" DO NOT SAY ANYTHING ELSE OTHER THAN THAT
Return the result as JSON, listing for each day the scheduled subjects, room, faculty, and enrolled students.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        timetable_json = response.text.strip()

        if timetable_json.startswith("```json") and timetable_json.endswith("```"):
            timetable_json = timetable_json[7:-3].strip()

        output_path = os.path.join(UPLOAD_FOLDER, "generated_timetable.json")
        with open(output_path, "w") as f:
            f.write(timetable_json)

        if timetable_json.startswith("Invalid"):
            return redirect(url_for('failure'))
        else:
            return redirect(url_for('timetable'))
    except Exception as e:
        return f"<h2>Error generating timetable: {e}</h2>", 500


@app.route('/failure')
def failure():
    output_path = os.path.join(UPLOAD_FOLDER, "generated_timetable.json")
    reason = "❌ Invalid arrangement. Please try again."

    try:
        with open(output_path, "r") as f:
            reason = f.read().strip()
            reason = reason.split(":")[1].strip()
    except Exception as e:
        reason = f"❌ Could not load error reason. ({e})"

    return render_template_string(f"<h2>{reason}</h2>")


@app.route('/timetable')
def timetable():
    output_path = os.path.join(UPLOAD_FOLDER, "generated_timetable.json")
    if not os.path.exists(output_path):
        return "<h2>No timetable generated yet.</h2>"

    with open(output_path, "r") as f:
        timetable_data = json.load(f)

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Generated Timetable</title>
<style>
    body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
    h1 { text-align: center; margin-bottom: 40px; }
    .day-section { margin-bottom: 40px; }
    .day-section h2 { background: #4caf50; color: white; padding: 10px; border-radius: 5px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #fff; box-shadow: 0 0 5px #ccc; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    th { background: #eee; }
    .students-list { font-size: 0.9em; color: #333; }
    @media (max-width: 768px) {
        table, thead, tbody, th, td, tr { display: block; }
        th { position: sticky; top: 0; background: #eee; }
        td { border: none; border-bottom: 1px solid #ccc; padding-left: 50%; position: relative; }
        td:before {
            position: absolute;
            left: 10px;
            width: 45%;
            white-space: nowrap;
            font-weight: bold;
        }
        td:nth-of-type(1):before { content: "Time"; }
        td:nth-of-type(2):before { content: "Subject"; }
        td:nth-of-type(3):before { content: "Room"; }
        td:nth-of-type(4):before { content: "Faculty"; }
        td:nth-of-type(5):before { content: "Course"; }
        td:nth-of-type(6):before { content: "Students"; }
    }
</style>
</head>
<body>
<h1>Generated Timetable</h1>
"""

    timetable = timetable_data.get("timetable", {})
    for day, sessions in timetable.items():
        html += f'<div class="day-section"><h2>{day}</h2>'
        html += '<table><tr><th>Time</th><th>Subject</th><th>Room</th><th>Faculty</th><th>Course</th><th>Enrolled Students</th></tr>'
        for session in sessions:
            students = ", ".join(session.get("enrolled_students", []))
            html += f'<tr>'
            html += f'<td>{session.get("time","")}</td>'
            html += f'<td>{session.get("subject","")}</td>'
            html += f'<td>{session.get("room","")}</td>'
            html += f'<td>{session.get("faculty","")}</td>'
            html += f'<td>{session.get("course","")}</td>'
            html += f'<td class="students-list">{students}</td>'
            html += f'</tr>'
        html += '</table></div>'

    html += "</body></html>"

    return render_template_string(html)


if __name__ == "__main__":
    app.run(debug=True)
