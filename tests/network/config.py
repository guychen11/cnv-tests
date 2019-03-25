from tests.config import *  # noqa: F403,F401


NETWORK_NS = "network-tests-namespace"
SVC_CMD = f"create serviceaccount privileged-test-user -n {NETWORK_NS}"  # noqa: F405
SVC_DELETE_CMD = f"delete serviceaccount privileged-test-user -n {NETWORK_NS}"  # noqa: F405
ADM_CMD = "adm policy add-scc-to-user privileged -z privileged-test-user"

#  PODS
PRIVILEGED_DAEMONSET_YAML = "tests/manifests/privileged-pod-ds.yml"
