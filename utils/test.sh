#!/bin/bash

for f in /*.yaml
do
  echo "applying $f ..."
  kubectl apply -f "$f"
done

kubectl get secret test-regcred
if [ $? -ne 0 ]; then
    echo "Could not find secret test-regcred"
    exit 1
fi
kubectl get secret test-scope
if [ $? -ne 0 ]; then
    echo "Could not find secret test-scope"
    exit 1
fi
kubectl get secret test-secret
if [ $? -ne 0 ]; then
    echo "Could not find secret test-secret"
    exit 1
fi
kubectl get secret test-template
if [ $? -ne 0 ]; then
    echo "Could not find secret test-template"
    exit 1
fi