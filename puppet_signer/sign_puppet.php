<?php
#Just a quick nasty hack to sign servers against our puppetmaster for AWS instances.

#there's the more correct way of doing things however this presents very specific design issues:
#Too many calls out to the AWS API, lack of naming standard in AWS.
#https://puppet.com/docs/puppet/5.5/ssl_autosign.html#concept-9595

#Author Name: Tony Welder
#Author Email: twelder@telligen.com

set_include_path(get_include_path() . PATH_SEPARATOR . 'phpseclib');

include('Net/SSH2.php');
include('Crypt/RSA.php');

$puppetAuthKey = htmlspecialchars($_POST["puppet_auth_key"]);
$hostnameForCertRequest = htmlspecialchars($_POST["hostname_for_cert_request"]);
$puppetMaster = "dmnocppup02.telligen.us";
$username = "AWScertsigner";
$privateKeyPath = "/opt/telligen/awscertsigner/awscertsigner.priv";
$crapKey = "replace is random large key";

function getRealIpAddr() {
  if (!empty($_SERVER['HTTP_CLIENT_IP'])){   //check ip from share internet{
    $ip=$_SERVER['HTTP_CLIENT_IP'];
  }
  elseif (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])){   //to check ip is pass from proxy{
    $ip=$_SERVER['HTTP_X_FORWARDED_FOR'];
  } else {
    $ip=$_SERVER['REMOTE_ADDR'];
  }
  return $ip;
}


if (strcmp($puppetAuthKey,$crapKey) !== 0) {
  # key didn't match so we're going to kill the session
  //I'm being intentially vague on feedback, don't want folks to know this requires a key
  exit('request failed!');
} else {
  # if the requesting ip isn't coming from our AWS IP range, kill the session.
  if (strpos(getRealIpAddr(),"10.100.") !== 0 && strpos(getRealIpAddr(),"172.26.") !== 0) {
    # if (preg_match("((10\\.100\\.)|(172\\.26\\.))",getRealIpAddr()) !== 0 ){
    exit('request failed!!');
  } else {
    #requesting IP is coming from a private network, we're good
    $key = new Crypt_RSA();
    $key->loadKey(file_get_contents($privateKeyPath));
    $ssh = new Net_SSH2($puppetMaster);
    if (!$ssh->login($username, $key)) {
      exit('Login Failed to Puppet Master');
    }
    $signingOutput = $ssh->exec("sudo /opt/puppetlabs/bin/puppet cert sign {$hostnameForCertRequest}");
    if (strpos($signingOutput,"Error") !== 0){
      exit('Failed to sign certificate');
    } else {
    echo "signed {$hostnameForCertRequest}";
    }
    #echo $ssh->exec("echo 'thomas is super cool'");

  }
}
?>
