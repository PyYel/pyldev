# VLLM deployment

This repository is purposefully made very simple. It might not be the most prod ready one, but it is reliable and upgradable.

## Deploying

To deploy in a cluster, the global behaviour is:

```bash
# First install
path/repo_name/folder_name> helm install <folder_name> .

# Upgrading
path/repo_name/folder_name> helm upgrade <folder_name> .
```

For instance, litellm pod deployment would be:

```bash
# First install
path/repo_name/litellm> helm install litellm .

# Upgrading
path/repo_name/litellm> helm upgrade litellm .
```

## Tainting GPU node

To prevent regular cpu-bound pods to be deployed on the gpu node, taint it:

```bash
# NoSchedule to prevent new pod from starting, NoExecute to even remove existing untagged pods
kubectl taint nodes <gpu-node-name> dedicated=gpu:NoExecute
```


## Testing

If a service is not exposed externally (only the frontend should), check the available services:

``kubectl get services``

In the list, find the service IP to test, and forward it:

``kubectl port-forward svc/litellm-service 4000:4000``

## Scaling in/out

This scales the number of pods in the namespace. Useful to shutdown the app for instance.

Turn it off:

``kubectl scale deployment --all --replicas=0 -n cyber-ai``

To turn it on:

``kubectl scale deployment --all --replicas=1 -n cyber-ai``


## Files structure

### Charts.yaml

We do not care. Yet.

### values.yaml

One value for one pod, for one microservice, for one image, for one container... In the case of vllm, see details below:

- vllm: Instead of having multiple values for each deployment, one values file defines multiples pods. Deployment loops the file content, starting one llm pod for each model section.
- litellm: upon updating models in vllm ``values``, the litellm config (in ``files/litellm-config.yaml``) must be updated too

### deployment.yaml

Definition of the pod, most of the relevant tweakable values are found in parent ``values.yaml``.

### pvc

A volume if needed. In the case of vllm, it is useful so starting a pod won't download the weights again, but instead load those from the volume cache (``.cache/huggingface``).

Note that pods should mostly be stateless (unless it's a DB or a permanent storage).

### service

Defines egress/ingress. ``ClusterIP`` in most cases, because microservices are not meant to be exposed. Service domain is named after its pod name.

