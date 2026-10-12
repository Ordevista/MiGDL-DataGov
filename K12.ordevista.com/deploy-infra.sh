#!/usr/bin/env bash
# Create or update the AWS stack for k12.ordevista.com.
# DNS for ordevista.com is managed at Bluehost, so this script prints the exact
# records to add there and waits while you add them.
#
#   ./deploy-infra.sh                       # k12.ordevista.com, DNS at Bluehost
#   ./deploy-infra.sh other.ordevista.com   # a different hostname
set -euo pipefail
cd "$(dirname "$0")"
DOMAIN="${1:-k12.ordevista.com}"
APEX="ordevista.com"
STACK="${STACK:-ordevista-resources}"
export AWS_REGION=us-east-1

hr() { printf '%*s\n' 72 '' | tr ' ' '-'; }
host_part() { local n="${1%.}"; echo "${n%.$APEX}"; }   # strip trailing dot and apex

echo "Deploying stack '$STACK' for https://$DOMAIN/ ..."
aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file infra/site.yaml \
  --parameter-overrides DomainName="$DOMAIN" HostedZoneId="" \
  --no-fail-on-empty-changeset &
DEPLOY_PID=$!

# Wait for the certificate request, then show the validation record for Bluehost.
CERT_ARN=""
for _ in $(seq 1 90); do
  CERT_ARN="$(aws cloudformation describe-stack-resources --stack-name "$STACK" \
      --logical-resource-id Certificate \
      --query 'StackResources[0].PhysicalResourceId' --output text 2>/dev/null || true)"
  [[ "$CERT_ARN" == arn:* ]] && break
  CERT_ARN=""
  kill -0 "$DEPLOY_PID" 2>/dev/null || break
  sleep 10
done

if [[ -n "$CERT_ARN" ]]; then
  read -r STATUS VNAME VVALUE < <(aws acm describe-certificate --certificate-arn "$CERT_ARN" \
    --query 'Certificate.DomainValidationOptions[0].[ValidationStatus,ResourceRecord.Name,ResourceRecord.Value]' \
    --output text)
  hr
  if [[ "$STATUS" == "SUCCESS" ]]; then
    echo "Certificate already validated. Nothing to add at Bluehost for step 1."
  else
    echo "BLUEHOST STEP 1 of 2: certificate validation record (add it now, then leave it forever)"
    echo
    echo "  Type      : CNAME"
    echo "  Host      : $(host_part "$VNAME")"
    echo "  Points To : ${VVALUE%.}"
    echo "  TTL       : leave the default"
    echo
    echo "The stack will continue on its own once AWS sees this record"
    echo "(usually 5-30 minutes after you save it)."
  fi
  hr
fi

if ! wait "$DEPLOY_PID"; then
  echo "Stack deployment failed. See CloudFormation > $STACK > Events in the AWS console." >&2
  exit 1
fi

CF_DOMAIN="$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='DistributionDomain'].OutputValue" --output text)"
hr
echo "BLUEHOST STEP 2 of 2: point $DOMAIN at CloudFront"
echo
echo "  Type      : CNAME"
echo "  Host      : $(host_part "$DOMAIN")"
echo "  Points To : $CF_DOMAIN"
echo "  TTL       : leave the default"
echo
echo "Test before DNS is ready: https://$CF_DOMAIN/  (after ./publish.sh)"
hr
