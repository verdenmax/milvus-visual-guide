"""Single source of truth: ordered map of output filename -> bilingual content.

Each value is a dict ``{"zh": html, "en": html}``. build.py and build_print.py
both import this so the lesson set stays in sync with shell.PAGES.

Grows one Part module per milestone (part1 .. part10).
"""
import part1
import part2
import part3

# Filename -> {"zh": ..., "en": ...}. Keep keys in sync with shell.PAGES.
CONTENT = {
    "01-what-is-milvus.html": part1.LESSON_01,
    "02-project-map.html": part1.LESSON_02,
    "03-life-of-a-request.html": part1.LESSON_03,
    "04-embeddings-and-similarity.html": part2.LESSON_04,
    "05-ann-algorithms.html": part2.LESSON_05,
    "06-data-model.html": part2.LESSON_06,
    "07-segments.html": part2.LESSON_07,
    "08-dependencies-and-deployment.html": part2.LESSON_08,
    "09-control-vs-data-plane.html": part3.LESSON_09,
    "10-proxy.html": part3.LESSON_10,
    "11-rootcoord.html": part3.LESSON_11,
    "12-datacoord.html": part3.LESSON_12,
    "13-querycoord.html": part3.LESSON_13,
    "14-metadata-and-coordination.html": part3.LESSON_14,
}
