deployment_name ?= bitwarden-crd-operator
namespace ?= bitwarden-crd-operator
label_filter = -l app.kubernetes.io/instance=bitwarden-crd-operator -l app.kubernetes.io/name=bitwarden-crd-operator

create-namespace:
	kubectl create namespace ${namespace}

dev:
	skaffold dev -n ${namespace}

run:
	skaffold run -n ${namespace}

pods:
	kubectl -n ${namespace} get pods

desc-pods:
	kubectl -n ${namespace} describe pod ${label_filter}

delete-pods-force:
	kubectl -n ${namespace} delete pod ${label_filter} --force

exec:
	kubectl -n ${namespace} exec -it deployment/${deployment_name} -- sh

logs:
	kubectl -n ${namespace} logs -f --tail 30 deployment/${deployment_name}