# youtube-automation

**Your YouTube numbers. Every day. By itself.** No copying from YouTube Studio by hand.

Daily YouTube data pipeline: API, cleaning, quality checks, history and logs. Runs on GitHub Actions.

## What it does for a YouTube channel

Every day this project collects the numbers of all videos on a channel, cleans them, checks them and saves them in a table. Nobody needs to open YouTube Studio or copy numbers by hand.

- **No password needed.** Only public data is used: views, likes, comments, publish date and video length.
- **Runs by itself.** It runs every day on a schedule. No computer needs to stay on.
- **History.** Every day is saved, so you can see how each video grows over time, not only the total.

## Example result

Data from my small test channel, collected automatically on 28 October 2026:

| Title | Published | Length (min) | Views | Likes | Comments | Date |
|---|---|---|---|---|---|---|
| Ocean from above | 2026-10-06 | 0.68 | 1 | 0 | 0 | 2026-10-28 |
| Ocean waves | 2026-10-06 | 0.13 | 2 | 0 | 0 | 2026-10-28 |

A new row for every video is added each day.

## What happens every day

1. **Collect.** The YouTube Data API returns the list of all channel videos, page by page, so channels with more than 50 videos are fully collected.
2. **Clean.** Numbers become real numbers, dates get one format, video length is turned into seconds and minutes, extra spaces and hidden characters are removed from titles.
3. **Check.** The data is checked for duplicates, wrong video IDs, negative values and missing numbers (for example, hidden likes).
4. **Save.** A table for the day is saved, and it is added to one history file.
5. **Log.** Every step is written to a log file, so any problem is easy to find.

If YouTube does not answer, the code tries again up to 3 times. If one channel fails, the other channels still run.

## Files

- `youtube_pipeline.py` — the main code
- `config.json` — list of channels. A new channel is added here, without changing the code
- `.github/workflows/daily.yml` — the daily schedule (GitHub Actions)
- `data/<channel>/channel_history.csv` — all days in one table
- `data/<channel>/videos_<date>.csv` — the table for one day
- `data/pipeline.log` — the log

## Security

The API key is stored in GitHub Secrets, not in the code.

## Next step

Integration: sending the clean table to Google Sheets, Looker Studio, email or Telegram.

Contact: https://www.linkedin.com/in/kanat-kaiykhov-84b84728a/
