export REPO_CLONE_DIR="/Users/venkat/code/dailybread/pys/clonerepos"
export OUTPUT_JSON="/Users/venkat/code/dailybread/pys/clonerepos/output.json"
export GITLAB_SOURCE_BRANCH="SRE-751-keep-traceid-spanid-in-the-log4j"
export GITLAB_TARGET_BRANCH="develop"
export GITLAB_URL="https://gitlab.com/"
export GITLAB_TOKEN=""
export CUSTOM_MESSAGE="[%d{ISO8601_OFFSET_DATE_TIME_HHCMM}][%X{X-Unique-ID}][trace.id=%equals{%X{trace.id}}{}{%X{trace_id}}][span.id=%X{span_id}][tx.id=%X{transaction.id}][%p] %c{3} - %m%n"
export PATTERN_LAYOUT_PATTERN="<Properties[^>]*>(.*?)<\/Properties>"
export GITLAB_COMMIT_MESSAGE="feat: SRE-751 keep trace.id and span.id in the log4j"
export MICROSERVICE_REPOS='{"47737232": "git@gitlab.com:dailybread/restaurant.git"}'
python3 Log4Updater.py