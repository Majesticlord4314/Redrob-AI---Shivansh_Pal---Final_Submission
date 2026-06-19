# Stage-3 reproduction image. The ranker is pure stdlib, so no pip install is
# needed and the build is fully deterministic.
#
#   docker build -t redrob-ranker .
#   docker run --rm -v "$PWD/data:/data" redrob-ranker \
#       --candidates /data/candidates.jsonl --out /data/submission.csv
#
# Constraints honored at run time: CPU only, no network, well under 5 min / 16 GB.
FROM python:3.11-slim

WORKDIR /app
COPY redrob/ ./redrob/
COPY rank.py ./

# No third-party dependencies. (requirements.txt is intentionally empty.)
ENTRYPOINT ["python", "rank.py"]
CMD ["--candidates", "/data/candidates.jsonl", "--out", "/data/submission.csv"]
