"""Free market-positioning data for intraday research (run on your PC; the research container cannot reach these hosts):
  python -m qpl.live.flow_data
SqueezeMetrics DIX / GEX daily history (https://squeezemetrics.com/monitor/dix -> "Download"): saved to research_data/more2/squeeze_dix.csv.
If the automatic download is refused (the site may need a browser), open the URL below in your browser and save the file as
research_data/more2/squeeze_dix.csv yourself."""
import sys
import urllib.request
from pathlib import Path
OUT = Path(__file__).resolve().parents[3] / "research_data/more2"
URL = "https://squeezemetrics.com/monitor/static/DIX.csv"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=60).read()
        (OUT / "squeeze_dix.csv").write_bytes(raw)
        print("saved", OUT / "squeeze_dix.csv", len(raw), "bytes")
        print(raw.decode(errors="ignore").splitlines()[:3])
    except Exception as e:                                      # noqa: BLE001
        print("Automatic download failed:", e)
        print("Open", URL, "in your browser and save it as", OUT / "squeeze_dix.csv")
        sys.exit(1)


if __name__ == "__main__":
    main()
