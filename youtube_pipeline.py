# ---------- 1. Imports ----------
import os
import json
import time
import logging
from datetime import date

import requests
import pandas as pd

# ---------- 2. Settings ----------
API_KEY = os.environ.get('YOUTUBE_API_KEY')

with open('config.json') as f:
    CONFIG = json.load(f)

BASE_FOLDER = CONFIG['base_folder']
os.makedirs(BASE_FOLDER, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(BASE_FOLDER + 'pipeline.log'),
              logging.StreamHandler()],
    force=True
)

# ---------- 3. Functions ----------
def safe_get(url, params, tries=3):
    for attempt in range(1, tries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            logging.warning(f'Attempt {attempt}: status {response.status_code}')
        except Exception as e:
            logging.warning(f'Attempt {attempt}: {type(e).__name__}')
        time.sleep(2)
    logging.error(f'All {tries} attempts failed')
    return None


def get_video_ids(channel_id):
    url_ch = 'https://www.googleapis.com/youtube/v3/channels'
    params_ch = {'part': 'contentDetails', 'id': channel_id, 'key': API_KEY}
    channel = safe_get(url_ch, params_ch)['items'][0]
    uploads_id = channel['contentDetails']['relatedPlaylists']['uploads']

    url_pl = 'https://www.googleapis.com/youtube/v3/playlistItems'
    video_ids = []
    next_token = None

    while True:
        params_pl = {'part': 'contentDetails', 'playlistId': uploads_id,
                     'maxResults': 50, 'key': API_KEY}
        if next_token:
            params_pl['pageToken'] = next_token

        page = safe_get(url_pl, params_pl)

        for item in page['items']:
            video_ids.append(item['contentDetails']['videoId'])

        next_token = page.get('nextPageToken')
        if next_token is None:
            break

    return video_ids


def get_videos_table(video_ids):
    url = 'https://www.googleapis.com/youtube/v3/videos'
    rows = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        params = {'part': 'snippet,statistics,contentDetails',
                  'id': ','.join(batch), 'key': API_KEY}
        data = safe_get(url, params)

        for video in data['items']:
            stats = video['statistics']
            rows.append({
                'video_id': video['id'],
                'title': video['snippet']['title'],
                'published_at': video['snippet']['publishedAt'],
                'views': stats.get('viewCount'),
                'likes': stats.get('likeCount'),
                'comments': stats.get('commentCount'),
                'duration_raw': video['contentDetails']['duration']
            })

    return pd.DataFrame(rows)


def clean_videos(df):
    df = df.copy()
    for col in ['views', 'likes', 'comments']:
        df[col] = pd.to_numeric(df[col])
    df['published_at'] = pd.to_datetime(df['published_at'])
    df['duration_sec'] = pd.to_timedelta(df['duration_raw']).dt.total_seconds().astype(int)
    df['duration_min'] = (df['duration_sec'] / 60).round(2)
    df = df.drop(columns=['duration_raw'])
    df['title'] = (df['title']
        .str.replace('\u200b', '', regex=False)
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip())
    return df


def check_quality(df):
    problems = 0
    cols = ['views', 'likes', 'comments']

    dups = df['video_id'].duplicated().sum()
    if dups > 0:
        logging.warning(f'Duplicate video_id: {dups}')
        problems += 1

    bad_ids = (df['video_id'].str.len() != 11).sum()
    if bad_ids > 0:
        logging.warning(f'Invalid video_id length: {bad_ids}')
        problems += 1

    negatives = (df[cols] < 0).sum().sum()
    if negatives > 0:
        logging.warning(f'Negative values: {negatives}')
        problems += 1

    missing = df[cols].isnull().sum().sum()
    if missing > 0:
        logging.warning(f'Missing values (maybe hidden likes): {missing}')
        problems += 1

    if problems == 0:
        logging.info('Quality check passed')
    return problems


def save_snapshot(df, folder):
    today = date.today().isoformat()
    df = df.copy()
    df['snapshot_date'] = today

    os.makedirs(folder, exist_ok=True)
    df.to_csv(folder + 'videos_' + today + '.csv', index=False)

    history_file = folder + 'channel_history.csv'
    if os.path.exists(history_file):
        history = pd.read_csv(history_file)
        history = pd.concat([history, df], ignore_index=True)
    else:
        history = df

    history = history.drop_duplicates(subset=['video_id', 'snapshot_date'], keep='last')
    history.to_csv(history_file, index=False)
    return history


def run_pipeline(channel_id, folder):
    logging.info(f'Start: channel {channel_id}')

    ids = get_video_ids(channel_id)
    logging.info(f'Video IDs collected: {len(ids)}')

    if len(ids) == 0:
        logging.warning('No videos found. Stop.')
        return None

    raw = get_videos_table(ids)
    clean = clean_videos(raw)
    logging.info(f'Clean table: {len(clean)} rows')

    check_quality(clean)

    history = save_snapshot(clean, folder)
    logging.info(f'History saved: {len(history)} rows')

    logging.info('Finish')
    return history


def run_pipeline_safe(channel_id, folder):
    try:
        return run_pipeline(channel_id, folder)
    except Exception as e:
        logging.error(f'Pipeline failed for {channel_id}: {type(e).__name__}')
        return None

# ---------- 4. Start ----------
def main():
    if not API_KEY:
        logging.error('No API key. Set YOUTUBE_API_KEY.')
        return

    for name, channel_id in CONFIG['channels'].items():
        channel_folder = BASE_FOLDER + name + '/'
        logging.info(f'--- Channel: {name} ---')
        run_pipeline_safe(channel_id, channel_folder)


if __name__ == '__main__':
    main()
