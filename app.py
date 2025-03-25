from builtins import Exception
from flask import Flask, request, jsonify, render_template
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import random
import time

# Download NLTK resources - fix the resource path
nltk.download('vader_lexicon')

# Initialize Flask app
app = Flask(__name__)

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

# Spotify API credentials (Use environment variables in production)
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID", "0678444341a04746a11c582347dfd97d")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET", "2ab8c12781e24ccaa115e0540cf6c650")

# Initialize Spotify client with proper error handling
try:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    ))
except Exception as e:
    import logging
    logging.error(f"Error initializing Spotify API: {e}")
    sp = None

# Enhanced mood analysis with more granular detection
def get_mood(text):
    sentiment = sia.polarity_scores(text)
    compound = sentiment["compound"]
    
    # More detailed mood mapping based on sentiment scores
    if compound >= 0.5:
        if "love" in text.lower() or "happy" in text.lower():
            return "euphoric"
        return "happy"
    elif 0.1 <= compound < 0.5:
        if "relax" in text.lower() or "calm" in text.lower():
            return "relaxed"
        return "positive"
    elif -0.1 <= compound < 0.1:
        if "tired" in text.lower() or "bored" in text.lower():
            return "chill"
        return "neutral"
    elif -0.5 <= compound < -0.1:
        if "stress" in text.lower() or "anxiety" in text.lower():
            return "anxious"
        return "melancholic"
    else:
        if "angry" in text.lower() or "hate" in text.lower():
            return "angry"
        return "sad"

# Enhanced song recommendation with more granular mood mapping
def recommend_songs(mood):
    # Expanded mood-to-genre mapping for more diversity
    mood_to_genres = {
        "happy": ["pop", "dance", "funk", "electronic", "disco"],
        "euphoric": ["edm", "house", "dance pop", "electro house", "tropical house"],
        "positive": ["indie pop", "pop rock", "feel-good", "sunshine pop", "tropical"],
        "neutral": ["alternative", "indie", "pop rock", "adult contemporary"],
        "relaxed": ["chill", "lofi", "ambient", "acoustic", "sleep"],
        "chill": ["lo-fi", "trip hop", "downtempo", "chillwave", "ambient"],
        "melancholic": ["indie folk", "soft rock", "slow", "ballad", "sad"],
        "anxious": ["post-rock", "experimental", "cinematic", "instrumental"],
        "sad": ["acoustic", "piano", "blues", "folk", "sad"],
        "angry": ["rock", "metal", "hardcore", "punk", "grunge"]
    }
    
    # Default to neutral if mood not found
    genres = mood_to_genres.get(mood, mood_to_genres["neutral"])
    
    # Pick a random genre from the list for variety
    selected_genre = random.choice(genres)
    
    # Add mood as seed for better results
    try:
        if sp is None:
            raise Exception("Spotify client not initialized")
            
        results = sp.search(q=f"genre:{selected_genre}", type="track", limit=10)
        
        # Extract song details, including album image
        songs = []
        for track in results["tracks"]["items"]:
            album_image_url = track["album"]["images"][0]["url"] if track["album"]["images"] else None
            
            # Handle missing data gracefully
            song = {
                "name": track["name"],
                "artist": track["artists"][0]["name"] if track["artists"] else "Unknown Artist",
                "url": track["external_urls"].get("spotify", "#"),
                "album_image": album_image_url,
            }
            songs.append(song)
            
        return songs
    except Exception as e:
        import logging
        logging.error(f"Error recommending songs: {e}")
        # Return sample data in case of API error
        return [
            {
                "name": "Sample Song for " + mood,
                "artist": "Sample Artist",
                "url": "https://open.spotify.com",
                "album_image": "https://via.placeholder.com/300"
            }
        ]

# Flask Routes
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        data = request.json
        user_input = data.get("text", "").strip()
        
        if not user_input:
            return jsonify({"error": "Please share how you're feeling"}), 400
        
        # Add artificial delay for loading state demo (remove in production)
        if app.debug:
            time.sleep(1)
        
        mood = get_mood(user_input)
        songs = recommend_songs(mood)
        
        return jsonify({"mood": mood, "songs": songs})
        
    except Exception as e:
        import logging
        logging.error(f"Error in /recommend: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error. Our team has been notified."}), 500

if __name__ == "__main__":
    app.run(debug=True)
