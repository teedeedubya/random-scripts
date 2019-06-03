#!/bin/bash
#Description: just a small helper script that will execute cloudformation against a AWS account.  Meant to be executed within context of quickbuild

#Dependencies: AWS CLI, JQ(yum package), AWS account with privs and configured aws cli profile



#### Passed Arguments ####
stackName="$1"
profile="$2"
#these paths should be relative, not absolute
pathToCFNTemplate="$3"
pathToCFNParameters="$4"


#### Commands ####
AWS='/usr/bin/aws'
JQ='/usr/bin/jq'
GREP='/bin/grep'
ECHO='/bin/echo'
AWK='/bin/awk'
SLEEP='/bin/sleep'
TR='/usr/bin/tr'

### Convenience Variables####
#capabilities="CAPABILITY_IAM,CAPABILITY_NAMED_IAM"
capabilities="CAPABILITY_IAM"


validate_template(){
  output="$(${AWS} cloudformation validate-template --template-body file://${pathToCFNTemplate} --profile ${profile})"
  if [ $? -eq 0 ]; then
    $ECHO "Template passed validation"
    return 0
  else
    $ECHO "Template failed validation"
    $ECHO "${output}"
    exit 1
  fi
}

#reports back the state of the current cloudformation, there is a 60 minute timeout
check_cloudformation_status(){
  cloudformationJSON="$1"
  stackModification="$2"
  stackModificationUpperCase=`$AWK '{print toupper($0)}'`
  if [[ $cloudformationJSON == *"ValidationError"* ]]; then
    #Since we already validated this template in a previous function, we know it's valid.
    #This is to deal with a edgecase where cloudformation returns a validation error if it detects
    #no changes.
    $ECHO "Cloudformation Detected no changes in ${pathToCFNTemplate}"
    exit 0
  else
     $ECHO $cloudformationJSON
     sleepCounter=1
     declare -A cloudformationResources
     $ECHO "$cloudformationJSON" > /tmp/caketown
     stackID=`$ECHO "$cloudformationJSON" | $JQ ".StackId" | $TR -d '"' | $TR -d "'"`
     while true;do
       resources=`$AWS cloudformation describe-stack-resources --stack-name $stackID --profile $profile --output text | $GREP "${stackModificationUpperCase}_COMPLETE" | $AWK '{print $2"     "$5}'`
       IFS=$'\n'
       for resource in $resources; do
         resourceName=`$ECHO $resource | $AWK '{print $1}'`
         if [ ${cloudformationResources[$resourceName]+_} ]; then
           $ECHO "already reported, nothing to do" > /dev/null
         else
           $ECHO "${resource}      ${stackModification} completed"
           cloudformationResources[$resourceName]=1
         fi
       done;
       unset $IFS
       #for polling for global status
       $AWS cloudformation describe-stacks --stack-name $stackID --profile $profile --output text | $GREP "${stackModificationUpperCase}_COMPLETE"
       if [ $? -eq 0 ]; then
         $ECHO "Cloudformation has finished executing"
         exit 0
       fi

       (( ++sleepCounter ))
       if [ $sleepCounter -gt 120 ]; then
         $ECHO "Cloudformation has executed for an hour, Deploy script is self terminating"
         $ECHO "Cloudformation will still continue to run in the background..."
         $ECHO "ERROR: self enforced timeout"
         exit 1
       fi
       $SLEEP 30
     done
  fi

}

validate_template

#check if stack exists
$AWS cloudformation list-stack-resources --stack-name $stackName  --profile $profile --output json > /dev/null 2>&1
if [ $? -eq 0 ]; then
  #Stack already exists
  $ECHO "Stack $StackName already exists, updating"
  cloudformationOutput="$($AWS cloudformation update-stack --stack-name $stackName --template-body file://${pathToCFNTemplate} \
    --parameters file://${pathToCFNParameters} --capabilities $capabilities --profile $profile --output json 2>&1)"
  check_cloudformation_status "$cloudformationOutput" "update"
else
  #Stack does not already exist
  $ECHO "Stack $StackName does not exist yet, creating"
  cloudformationOutput="$($AWS cloudformation create-stack --stack-name $stackName --template-body file://${pathToCFNTemplate} \
     --parameters file://${pathToCFNParameters} --capabilities $capabilities --profile $profile --output json 2>&1)"
  check_cloudformation_status "$cloudformationOutput" "create"
fi

