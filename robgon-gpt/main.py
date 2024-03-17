from flask import Flask, request, send_file, jsonify, abort
import os
from music21 import stream, harmony, tempo, instrument
import pandas as pd
import numpy as np
import markdown2
from functools import wraps

app = Flask(__name__)

# Your list of valid API keys
VALID_API_KEYS = {
    "your_api_key": "RobGonBot"
}

# Load the CSV file at app start
df = pd.read_csv('public_domain_songs.csv')

# Replace NaN values with empty strings
df.fillna('', inplace=True)

# Decorator to require an API key
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Retrieve the API key from the specified header
        api_key = request.headers.get('X-Api-Key')
        if api_key not in VALID_API_KEYS:
            # If the API key is not valid, return HTTP 401 Unauthorized
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

# Test endpoint
@app.route('/test')
def test():
    return "OK"

# Privacy policy endpoint
@app.route('/privacy_policy')
def privacy_policy():
    # Read the privacy policy from the file
    with open('privacy_policy.md', 'r') as file:
        privacy_policy_md = file.read()
    # Convert Markdown to HTML
    privacy_policy_html = markdown2.markdown(privacy_policy_md)
    return f'<div style="font-family: sans-serif;">{privacy_policy_html}</div>'

# Convert the chord string to a MIDI file
def chords_to_midi(chord_string):
    # chord_string = chord_string.replace("b", "-")
    chords_list = chord_string.split(' ')
    s = stream.Stream()
    s.append(tempo.MetronomeMark(number=120))
    s.append(instrument.Piano())
    for chord_symbol in chords_list:
        try:
            ch = harmony.ChordSymbol(chord_symbol)
            ch.duration.type = 'half'
            s.append(ch)
        except:
            pass
    file_name = "./midi/" + chord_string.replace(" ", "_") + ".mid"
    file_name = file_name.replace("/", "_")
    s.write('midi', fp=file_name)
    return file_name

# Download the MIDI file
@app.route("/download_midi")
def download_midi():
    chord_string = request.args.get('chords')
    if not chord_string:
        chord_string="C"
    midi_file_path = chords_to_midi(chord_string)
    return send_file(midi_file_path, as_attachment=True)

@app.route('/song_search')
@require_api_key
def song_search():
    # Get genre and style from query parameters
    genre = request.args.get('genre', default='no genre')
    style = request.args.get('style', default='no style')

    # Filter the DataFrame for songs that match the genre AND style
    matches_and = df[df['genres'].str.contains(genre, case=False, na=False) &
                     df['styles'].str.contains(style, case=False, na=False)]

    if len(matches_and) == 5:
        # If exactly 5 matches, return them
        matches_json = matches_and.to_dict(orient='records')
        return jsonify(matches_json)
    elif len(matches_and) > 5:
        # If more than 5, return 5 at random
        matches_random = matches_and.sample(n=5, random_state=np.random.RandomState())
        matches_json = matches_random.to_dict(orient='records')
        return jsonify(matches_json)
    else:
        # If less than 5, use OR to find additional matches
        matches_or = df[df['genres'].str.contains(genre, case=False, na=False) |
                        df['styles'].str.contains(style, case=False, na=False)]
        # Exclude already matched rows
        matches_or = matches_or[~matches_or.index.isin(matches_and.index)]
        # Calculate how many more matches are needed
        additional_needed = 5 - len(matches_and)
        # Get additional matches at random if available
        additional_matches = matches_or.sample(n=min(additional_needed, len(matches_or)), random_state=np.random.RandomState())
        # Combine the AND matches with the additional OR matches
        combined_matches = pd.concat([matches_and, additional_matches])
        combined_matches_json = combined_matches.to_dict(orient='records')
        return jsonify(combined_matches_json)

if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
