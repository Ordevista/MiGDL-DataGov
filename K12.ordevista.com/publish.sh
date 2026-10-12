#!/usr/bin/env bash
# Every time content changes: rebuild the page, upload it, and refresh the CDN.
set -euo pipefail
cd "$(dirname "$0")"
STACK="${STACK:-ordevista-resources}"
export AWS_REGION=us-east-1

out() { aws cloudformation describe-stacks --stack-name "$STACK" \
          --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
BUCKET="$(out BucketName)"
DIST_ID="$(out DistributionId)"

python3 src/build.py "$@"

# Long cache for logos and files, short cache for pages so updates show up fast.
aws s3 sync dist/ "s3://$BUCKET/" --delete \
  --exclude "*.html" --exclude "styles.css" --exclude "app.js" \
  --cache-control "public, max-age=86400"
aws s3 sync dist/ "s3://$BUCKET/" --delete \
  --exclude "*" --include "*.html" --include "styles.css" --include "app.js" \
  --cache-control "public, max-age=300"

aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" \
  --query "Invalidation.Id" --output text
echo "Published: $(out SiteUrl)"
