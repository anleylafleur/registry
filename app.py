from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"csv", "xlsx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return redirect(url_for("countries"))


@app.route("/countries")
def countries():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT CountryID, CountryName, FIFACode, ISOCode, CreatedDate
        FROM Countries
        ORDER BY CountryName
    """)

    rows = cursor.fetchall()
    conn.close()

    return render_template("countries.html", countries=rows, edit_country=None)


@app.route("/countries/add", methods=["POST"])
def add_country():
    country_name = request.form.get("CountryName")
    fifa_code = request.form.get("FIFACode")
    iso_code = request.form.get("ISOCode")

    if not country_name:
        flash("Country name is required.", "danger")
        return redirect(url_for("countries"))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Countries (CountryName, FIFACode, ISOCode)
            VALUES (?, ?, ?)
        """, country_name, fifa_code, iso_code)

        conn.commit()
        conn.close()

        flash("Country added successfully.", "success")

    except Exception as e:
        flash(f"Error adding country: {str(e)}", "danger")

    return redirect(url_for("countries"))


@app.route("/countries/edit/<int:country_id>")
def edit_country(country_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT CountryID, CountryName, FIFACode, ISOCode
        FROM Countries
        WHERE CountryID = ?
    """, country_id)

    edit_country = cursor.fetchone()

    cursor.execute("""
        SELECT CountryID, CountryName, FIFACode, ISOCode, CreatedDate
        FROM Countries
        ORDER BY CountryName
    """)

    rows = cursor.fetchall()
    conn.close()

    return render_template("countries.html", countries=rows, edit_country=edit_country)


@app.route("/countries/update/<int:country_id>", methods=["POST"])
def update_country(country_id):
    country_name = request.form.get("CountryName")
    fifa_code = request.form.get("FIFACode")
    iso_code = request.form.get("ISOCode")

    if not country_name:
        flash("Country name is required.", "danger")
        return redirect(url_for("countries"))

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Countries
            SET CountryName = ?,
                FIFACode = ?,
                ISOCode = ?
            WHERE CountryID = ?
        """, country_name, fifa_code, iso_code, country_id)

        conn.commit()
        conn.close()

        flash("Country updated successfully.", "success")

    except Exception as e:
        flash(f"Error updating country: {str(e)}", "danger")

    return redirect(url_for("countries"))


@app.route("/countries/delete/<int:country_id>", methods=["POST"])
def delete_country(country_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM Countries
            WHERE CountryID = ?
        """, country_id)

        conn.commit()
        conn.close()

        flash("Country deleted successfully.", "success")

    except Exception as e:
        flash(
            "Unable to delete country. It may already be linked to regions, clubs, players, or competitions.",
            "danger"
        )

    return redirect(url_for("countries"))


@app.route("/countries/upload", methods=["POST"])
def upload_countries():
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("Please select a CSV or Excel file.", "danger")
        return redirect(url_for("countries"))

    if not allowed_file(file.filename):
        flash("Only CSV and Excel files are allowed.", "danger")
        return redirect(url_for("countries"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)

        required_columns = ["CountryName", "FIFACode", "ISOCode"]

        for col in required_columns:
            if col not in df.columns:
                flash(f"Missing required column: {col}", "danger")
                return redirect(url_for("countries"))

        conn = get_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            country_name = str(row["CountryName"]).strip()

            if not country_name or country_name.lower() == "nan":
                skipped += 1
                continue

            fifa_code = None if pd.isna(row["FIFACode"]) else str(row["FIFACode"]).strip()
            iso_code = None if pd.isna(row["ISOCode"]) else str(row["ISOCode"]).strip()

            cursor.execute("""
                SELECT COUNT(*)
                FROM Countries
                WHERE CountryName = ?
            """, country_name)

            exists = cursor.fetchone()[0]

            if exists:
                skipped += 1
                continue

            cursor.execute("""
                INSERT INTO Countries (CountryName, FIFACode, ISOCode)
                VALUES (?, ?, ?)
            """, country_name, fifa_code, iso_code)

            inserted += 1

        conn.commit()
        conn.close()

        flash(f"Upload complete. Inserted: {inserted}, Skipped: {skipped}", "success")

    except Exception as e:
        flash(f"Upload failed: {str(e)}", "danger")

    return redirect(url_for("countries"))

@app.route("/players")
def players():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.PlayerID, p.FIFAID, p.NationalRegistrationNo,
            p.FirstName, p.MiddleName, p.LastName,
            p.DateOfBirth, p.Gender,
            nc.CountryName AS Nationality,
            cb.CountryName AS CountryOfBirth,
            pos.PositionName AS PrimaryPosition,
            pl.PlayerLevelName,
            p.PlayerStatus
        FROM Players p
        LEFT JOIN Countries nc ON p.NationalityCountryID = nc.CountryID
        LEFT JOIN Countries cb ON p.CountryOfBirthID = cb.CountryID
        LEFT JOIN Positions pos ON p.PrimaryPositionID = pos.PositionID
        LEFT JOIN PlayerLevels pl ON p.PlayerLevelID = pl.PlayerLevelID
        ORDER BY p.LastName, p.FirstName
    """)
    rows = cursor.fetchall()

    cursor.execute("SELECT CountryID, CountryName FROM Countries ORDER BY CountryName")
    countries = cursor.fetchall()

    cursor.execute("SELECT PositionID, PositionName FROM Positions ORDER BY PositionName")
    positions = cursor.fetchall()

    cursor.execute("SELECT PlayerLevelID, PlayerLevelName FROM PlayerLevels ORDER BY PlayerLevelName")
    player_levels = cursor.fetchall()

    conn.close()

    return render_template(
        "players.html",
        players=rows,
        edit_player=None,
        countries=countries,
        positions=positions,
        player_levels=player_levels
    )


@app.route("/players/add", methods=["POST"])
def add_player():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Players (
                FIFAID, NationalRegistrationNo, FirstName, MiddleName, LastName,
                DateOfBirth, Gender, NationalityCountryID, CountryOfBirthID,
                PreferredFoot, PrimaryPositionID, SecondaryPositionID,
                PlayerLevelID, PlayerStatus, HeightCM, WeightKG, Email, Phone
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        request.form.get("FIFAID"),
        request.form.get("NationalRegistrationNo"),
        request.form.get("FirstName"),
        request.form.get("MiddleName"),
        request.form.get("LastName"),
        request.form.get("DateOfBirth"),
        request.form.get("Gender"),
        request.form.get("NationalityCountryID") or None,
        request.form.get("CountryOfBirthID") or None,
        request.form.get("PreferredFoot"),
        request.form.get("PrimaryPositionID") or None,
        request.form.get("SecondaryPositionID") or None,
        request.form.get("PlayerLevelID") or None,
        request.form.get("PlayerStatus") or "Active",
        request.form.get("HeightCM") or None,
        request.form.get("WeightKG") or None,
        request.form.get("Email"),
        request.form.get("Phone")
        )

        conn.commit()
        conn.close()
        flash("Player added successfully.", "success")

    except Exception as e:
        flash(f"Error adding player: {str(e)}", "danger")

    return redirect(url_for("players"))


@app.route("/players/edit/<int:player_id>")
def edit_player(player_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Players WHERE PlayerID = ?", player_id)
    edit_player = cursor.fetchone()

    cursor.execute("SELECT CountryID, CountryName FROM Countries ORDER BY CountryName")
    countries = cursor.fetchall()

    cursor.execute("SELECT PositionID, PositionName FROM Positions ORDER BY PositionName")
    positions = cursor.fetchall()

    cursor.execute("SELECT PlayerLevelID, PlayerLevelName FROM PlayerLevels ORDER BY PlayerLevelName")
    player_levels = cursor.fetchall()

    cursor.execute("""
        SELECT 
            p.PlayerID, p.FIFAID, p.NationalRegistrationNo,
            p.FirstName, p.MiddleName, p.LastName,
            p.DateOfBirth, p.Gender,
            nc.CountryName AS Nationality,
            cb.CountryName AS CountryOfBirth,
            pos.PositionName AS PrimaryPosition,
            pl.PlayerLevelName,
            p.PlayerStatus
        FROM Players p
        LEFT JOIN Countries nc ON p.NationalityCountryID = nc.CountryID
        LEFT JOIN Countries cb ON p.CountryOfBirthID = cb.CountryID
        LEFT JOIN Positions pos ON p.PrimaryPositionID = pos.PositionID
        LEFT JOIN PlayerLevels pl ON p.PlayerLevelID = pl.PlayerLevelID
        ORDER BY p.LastName, p.FirstName
    """)
    rows = cursor.fetchall()

    conn.close()

    return render_template(
        "players.html",
        players=rows,
        edit_player=edit_player,
        countries=countries,
        positions=positions,
        player_levels=player_levels
    )


@app.route("/players/update/<int:player_id>", methods=["POST"])
def update_player(player_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Players
            SET FIFAID = ?,
                NationalRegistrationNo = ?,
                FirstName = ?,
                MiddleName = ?,
                LastName = ?,
                DateOfBirth = ?,
                Gender = ?,
                NationalityCountryID = ?,
                CountryOfBirthID = ?,
                PreferredFoot = ?,
                PrimaryPositionID = ?,
                SecondaryPositionID = ?,
                PlayerLevelID = ?,
                PlayerStatus = ?,
                HeightCM = ?,
                WeightKG = ?,
                Email = ?,
                Phone = ?,
                UpdatedDate = SYSDATETIME()
            WHERE PlayerID = ?
        """,
        request.form.get("FIFAID"),
        request.form.get("NationalRegistrationNo"),
        request.form.get("FirstName"),
        request.form.get("MiddleName"),
        request.form.get("LastName"),
        request.form.get("DateOfBirth"),
        request.form.get("Gender"),
        request.form.get("NationalityCountryID") or None,
        request.form.get("CountryOfBirthID") or None,
        request.form.get("PreferredFoot"),
        request.form.get("PrimaryPositionID") or None,
        request.form.get("SecondaryPositionID") or None,
        request.form.get("PlayerLevelID") or None,
        request.form.get("PlayerStatus") or "Active",
        request.form.get("HeightCM") or None,
        request.form.get("WeightKG") or None,
        request.form.get("Email"),
        request.form.get("Phone"),
        player_id
        )

        conn.commit()
        conn.close()
        flash("Player updated successfully.", "success")

    except Exception as e:
        flash(f"Error updating player: {str(e)}", "danger")

    return redirect(url_for("players"))


@app.route("/players/delete/<int:player_id>", methods=["POST"])
def delete_player(player_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM Players WHERE PlayerID = ?", player_id)

        conn.commit()
        conn.close()
        flash("Player deleted successfully.", "success")

    except Exception:
        flash("Unable to delete player. Player may be linked to registrations, matches, statistics, or documents.", "danger")

    return redirect(url_for("players"))


@app.route("/players/upload", methods=["POST"])
def upload_players():
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("Please select a CSV or Excel file.", "danger")
        return redirect(url_for("players"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)

        required_columns = ["FirstName", "LastName", "DateOfBirth"]

        for col in required_columns:
            if col not in df.columns:
                flash(f"Missing required column: {col}", "danger")
                return redirect(url_for("players"))

        conn = get_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            first_name = str(row["FirstName"]).strip()
            last_name = str(row["LastName"]).strip()
            dob = row["DateOfBirth"]

            if not first_name or not last_name or pd.isna(dob):
                skipped += 1
                continue

            cursor.execute("""
                SELECT COUNT(*)
                FROM Players
                WHERE FirstName = ? AND LastName = ? AND DateOfBirth = ?
            """, first_name, last_name, dob)

            exists = cursor.fetchone()[0]

            if exists:
                skipped += 1
                continue

            cursor.execute("""
                INSERT INTO Players (
                    FirstName, LastName, DateOfBirth, Gender,
                    FIFAID, NationalRegistrationNo, PlayerStatus
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            first_name,
            last_name,
            dob,
            None if "Gender" not in df.columns or pd.isna(row.get("Gender")) else str(row.get("Gender")).strip(),
            None if "FIFAID" not in df.columns or pd.isna(row.get("FIFAID")) else str(row.get("FIFAID")).strip(),
            None if "NationalRegistrationNo" not in df.columns or pd.isna(row.get("NationalRegistrationNo")) else str(row.get("NationalRegistrationNo")).strip(),
            "Active"
            )

            inserted += 1

        conn.commit()
        conn.close()

        flash(f"Upload complete. Inserted: {inserted}, Skipped: {skipped}", "success")

    except Exception as e:
        flash(f"Upload failed: {str(e)}", "danger")

    return redirect(url_for("players"))

@app.route("/scouting-reports")
def scouting_reports():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            sr.ScoutingReportID,
            p.FirstName + ' ' + p.LastName AS PlayerName,
            s.ScoutName,
            sr.ReportDate,
            sr.TechnicalRating,
            sr.TacticalRating,
            sr.PhysicalRating,
            sr.MentalRating,
            sr.OverallRating,
            sr.Recommendation
        FROM PlayerScoutingReports sr
        INNER JOIN Players p ON sr.PlayerID = p.PlayerID
        LEFT JOIN Scouts s ON sr.ScoutID = s.ScoutID
        ORDER BY sr.ReportDate DESC
    """)
    reports = cursor.fetchall()

    cursor.execute("""
        SELECT PlayerID, FirstName + ' ' + LastName AS PlayerName
        FROM Players
        ORDER BY LastName, FirstName
    """)
    players = cursor.fetchall()

    cursor.execute("""
        SELECT ScoutID, ScoutName
        FROM Scouts
        WHERE IsActive = 1
        ORDER BY ScoutName
    """)
    scouts = cursor.fetchall()

    conn.close()

    return render_template(
        "scouting_reports.html",
        reports=reports,
        players=players,
        scouts=scouts,
        edit_report=None
    )


@app.route("/scouting-reports/add", methods=["POST"])
def add_scouting_report():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO PlayerScoutingReports (
                PlayerID, ScoutID, ReportDate,
                TechnicalRating, TacticalRating, PhysicalRating,
                MentalRating, OverallRating,
                Strengths, Weaknesses, DevelopmentNotes,
                Recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        request.form.get("PlayerID"),
        request.form.get("ScoutID") or None,
        request.form.get("ReportDate"),
        request.form.get("TechnicalRating") or None,
        request.form.get("TacticalRating") or None,
        request.form.get("PhysicalRating") or None,
        request.form.get("MentalRating") or None,
        request.form.get("OverallRating") or None,
        request.form.get("Strengths"),
        request.form.get("Weaknesses"),
        request.form.get("DevelopmentNotes"),
        request.form.get("Recommendation")
        )

        conn.commit()
        conn.close()
        flash("Scouting report added successfully.", "success")

    except Exception as e:
        flash(f"Error adding scouting report: {str(e)}", "danger")

    return redirect(url_for("scouting_reports"))


@app.route("/scouting-reports/edit/<int:report_id>")
def edit_scouting_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM PlayerScoutingReports
        WHERE ScoutingReportID = ?
    """, report_id)
    edit_report = cursor.fetchone()

    cursor.execute("""
        SELECT 
            sr.ScoutingReportID,
            p.FirstName + ' ' + p.LastName AS PlayerName,
            s.ScoutName,
            sr.ReportDate,
            sr.TechnicalRating,
            sr.TacticalRating,
            sr.PhysicalRating,
            sr.MentalRating,
            sr.OverallRating,
            sr.Recommendation
        FROM PlayerScoutingReports sr
        INNER JOIN Players p ON sr.PlayerID = p.PlayerID
        LEFT JOIN Scouts s ON sr.ScoutID = s.ScoutID
        ORDER BY sr.ReportDate DESC
    """)
    reports = cursor.fetchall()

    cursor.execute("""
        SELECT PlayerID, FirstName + ' ' + LastName AS PlayerName
        FROM Players
        ORDER BY LastName, FirstName
    """)
    players = cursor.fetchall()

    cursor.execute("""
        SELECT ScoutID, ScoutName
        FROM Scouts
        WHERE IsActive = 1
        ORDER BY ScoutName
    """)
    scouts = cursor.fetchall()

    conn.close()

    return render_template(
        "scouting_reports.html",
        reports=reports,
        players=players,
        scouts=scouts,
        edit_report=edit_report
    )


@app.route("/scouting-reports/update/<int:report_id>", methods=["POST"])
def update_scouting_report(report_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE PlayerScoutingReports
            SET PlayerID = ?,
                ScoutID = ?,
                ReportDate = ?,
                TechnicalRating = ?,
                TacticalRating = ?,
                PhysicalRating = ?,
                MentalRating = ?,
                OverallRating = ?,
                Strengths = ?,
                Weaknesses = ?,
                DevelopmentNotes = ?,
                Recommendation = ?
            WHERE ScoutingReportID = ?
        """,
        request.form.get("PlayerID"),
        request.form.get("ScoutID") or None,
        request.form.get("ReportDate"),
        request.form.get("TechnicalRating") or None,
        request.form.get("TacticalRating") or None,
        request.form.get("PhysicalRating") or None,
        request.form.get("MentalRating") or None,
        request.form.get("OverallRating") or None,
        request.form.get("Strengths"),
        request.form.get("Weaknesses"),
        request.form.get("DevelopmentNotes"),
        request.form.get("Recommendation"),
        report_id
        )

        conn.commit()
        conn.close()
        flash("Scouting report updated successfully.", "success")

    except Exception as e:
        flash(f"Error updating scouting report: {str(e)}", "danger")

    return redirect(url_for("scouting_reports"))


@app.route("/scouting-reports/delete/<int:report_id>", methods=["POST"])
def delete_scouting_report(report_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM PlayerScoutingReports
            WHERE ScoutingReportID = ?
        """, report_id)

        conn.commit()
        conn.close()
        flash("Scouting report deleted successfully.", "success")

    except Exception as e:
        flash(f"Error deleting scouting report: {str(e)}", "danger")

    return redirect(url_for("scouting_reports"))


@app.route("/scouting-reports/upload", methods=["POST"])
def upload_scouting_reports():
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("Please select a CSV or Excel file.", "danger")
        return redirect(url_for("scouting_reports"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)

        required_columns = [
            "PlayerID",
            "ReportDate",
            "TechnicalRating",
            "TacticalRating",
            "PhysicalRating",
            "MentalRating",
            "OverallRating"
        ]

        for col in required_columns:
            if col not in df.columns:
                flash(f"Missing required column: {col}", "danger")
                return redirect(url_for("scouting_reports"))

        conn = get_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped = 0

        for _, row in df.iterrows():
            player_id = row["PlayerID"]
            report_date = row["ReportDate"]

            if pd.isna(player_id) or pd.isna(report_date):
                skipped += 1
                continue

            cursor.execute("SELECT COUNT(*) FROM Players WHERE PlayerID = ?", int(player_id))
            player_exists = cursor.fetchone()[0]

            if not player_exists:
                skipped += 1
                continue

            scout_id = None
            if "ScoutID" in df.columns and not pd.isna(row.get("ScoutID")):
                scout_id = int(row.get("ScoutID"))

            cursor.execute("""
                INSERT INTO PlayerScoutingReports (
                    PlayerID, ScoutID, ReportDate,
                    TechnicalRating, TacticalRating, PhysicalRating,
                    MentalRating, OverallRating,
                    Strengths, Weaknesses, DevelopmentNotes,
                    Recommendation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            int(player_id),
            scout_id,
            report_date,
            None if pd.isna(row["TechnicalRating"]) else int(row["TechnicalRating"]),
            None if pd.isna(row["TacticalRating"]) else int(row["TacticalRating"]),
            None if pd.isna(row["PhysicalRating"]) else int(row["PhysicalRating"]),
            None if pd.isna(row["MentalRating"]) else int(row["MentalRating"]),
            None if pd.isna(row["OverallRating"]) else int(row["OverallRating"]),
            None if "Strengths" not in df.columns or pd.isna(row.get("Strengths")) else str(row.get("Strengths")),
            None if "Weaknesses" not in df.columns or pd.isna(row.get("Weaknesses")) else str(row.get("Weaknesses")),
            None if "DevelopmentNotes" not in df.columns or pd.isna(row.get("DevelopmentNotes")) else str(row.get("DevelopmentNotes")),
            None if "Recommendation" not in df.columns or pd.isna(row.get("Recommendation")) else str(row.get("Recommendation"))
            )

            inserted += 1

        conn.commit()
        conn.close()

        flash(f"Upload complete. Inserted: {inserted}, Skipped: {skipped}", "success")

    except Exception as e:
        flash(f"Upload failed: {str(e)}", "danger")

    return redirect(url_for("scouting_reports"))

@app.route("/db-test")
def db_test():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        return f"DB OK: {result[0]}"
    except Exception as e:
        return f"DB ERROR: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)