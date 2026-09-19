# reddit-reader

A small personal-use Reddit CLI I run on my own machine as part of my development
workflow. It reads threads and comments from the subreddits I subscribe to
(r/redditdev, r/programming, r/LocalLLaMA, r/ChatGPTCoding, r/selfhosted) so I can
keep up with them for personal research, and it only ever writes when I type the
comment myself and confirm it.

This is a local, script-type OAuth app used with my own Reddit account
(u/Wild-Rush6576). It is not a service, not hosted anywhere, and not used by
anyone else.

## What it does

- **Read-only by default.** Lists my subscribed subreddits, pulls hot threads,
  and fetches comments for a thread. That is the day-to-day use.
- **Manual writes only.** The `comment` command prints exactly what will be sent
  and posts only after I review the text and confirm interactively. There is no
  scheduled, automatic, or bulk posting of any kind.
- **Low volume.** The script tracks its own API usage and refuses to go past
  ~100 API calls per day, well under Reddit's rate limits.

## Non-goals

This script does not and will not:

- manipulate votes or farm karma
- cross-post or post the same content to multiple subreddits
- scrape Reddit at scale or mirror subreddits
- sell, share, or redistribute Reddit data
- use Reddit data to train or evaluate AI/ML models

## Reddit API usage

OAuth2 installed-app flow. The authorization redirect goes to
`http://localhost:8080` where a tiny throwaway HTTP server catches the code.

Scopes requested:

| Scope         | Why                                                        |
| ------------- | ---------------------------------------------------------- |
| `identity`    | confirm the token belongs to my account                    |
| `mysubreddits`| list the subreddits I subscribe to (`/subreddits/mine/subscriber`) |
| `read`        | read threads and comments (`/r/<sub>/hot`, `/comments/<id>`) |
| `submit`      | post a comment I wrote and confirmed by hand (`/api/comment`) |

Endpoints used: `GET /api/v1/me`, `GET /subreddits/mine/subscriber`,
`GET /r/<sub>/hot`, `GET /comments/<article>`, `POST /api/comment` (manual only).

## Setup

1. Create an installed-app at https://www.reddit.com/prefs/apps with redirect
   URI `http://localhost:8080`.
2. `pip install -r requirements.txt`
3. Export config:
   ```sh
   export REDDIT_CLIENT_ID=...
   export REDDIT_CLIENT_SECRET=...   # empty for installed apps is fine
   ```
4. `python reddit_reader.py auth` — opens the consent URL, catches the
   localhost redirect, and stores the refresh token in
   `.reddit_reader_token.json` (gitignored).

## Usage

```sh
python reddit_reader.py --help               # or: python reddit_reader.py help
python reddit_reader.py subs                 # list my subscribed subreddits
python reddit_reader.py hot programming      # hot threads in r/programming
python reddit_reader.py comments <post_id>   # comments on one thread
python reddit_reader.py comment <post_id>    # write a comment by hand, review, confirm
```

`--help` (or `help`) prints the full command list with one-line descriptions
and exits 0. It needs no credentials and makes no API calls, so it works on a
clean checkout.

## License

MIT
