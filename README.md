# Bitwarden CRD Operator

[![Build Status](https://drone.uploadfilter24.eu/api/badges/lerentis/bitwarden-crd-operator/status.svg?ref=refs/heads/main)](https://drone.uploadfilter24.eu/lerentis/bitwarden-crd-operator)

Bitwarden CRD Operator is a kubernetes Operator based on [kopf](https://github.com/nolar/kopf/). The goal is to create kubernetes native secret objects from bitwarden.

> DISCLAIMER:  
> This project is still very work in progress :)

## Getting started

For now a few secrets need to be passed to helm. I will change this in the future to give the option to also use a kubernetes secret for this.

You will need a `ClientID` and `ClientSecret` ([where to get these](https://bitwarden.com/help/personal-api-key/)) as well as your password.
Expose these to the operator as described in this example:

```yaml
env:
  - name: BW_HOST
    value: "https://bitwarden.your.tld.org"
  - name: BW_CLIENTID
    value: "user.your-client-id"
  - name: BW_CLIENTSECRET
    value: "YoUrCliEntSecRet"
  - name: BW_PASSWORD
    value: "YourSuperSecurePassword"
```

`BW_HOST` can be omitted if you are using the Bitwarden SaaS offering.

After that it is a basic helm deployment:

```bash
kubectl create namespace bw-operator
helm upgrade --install --namespace bw-operator -f chart/bitwarden-crd-operator/values.yaml bw-operator chart/bitwarden-crd-operator
```

And you are set to create your first secret using this operator. For that you need to add a CRD Object like this to your cluster:

```yaml
---
apiVersion: "lerentis.uploadfilter24.eu/v1beta1"
kind: BitwardenSecret
metadata:
  name: name-of-your-management-object
spec:
  type: "UsernamePassword"
  id: "A Secret ID from bitwarden"
  name: "Name of the secret to be created"
  namespace: "Namespace of the secret to be created"
```

The ID can be extracted from the browser when you open a item the ID is in the URL. The resulting secret looks something like this:

```yaml
apiVersion: v1
data:
  password: "base64 encoded password"
  username: "base64 encoded username"
kind: Secret
metadata:
  annotations:
    managed: bitwarden-secrets.lerentis.uploadfilter24.eu
    managedObject: bw-operator/test
  name: name-of-your-management-object
  namespace: default
type: Opaque
```

## Short Term Roadmap

[] support more types  
[] offer option to use a existing secret in helm chart  
[] host chart on gh pages  
[] maybe extend spec to offer modification of keys as well
