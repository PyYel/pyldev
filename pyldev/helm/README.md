# VLLM deployment

This repository is purposefully made very simple. It might not be the most prod ready one, but it is reliable and upgradable.

## Deployement 

To deploy in a cluster, the global behaviour is:

```bash
# First install
path/repo_name/folder_name> helm install <folder_name> .

# Upgrading
path/repo_name/folder_name> helm install <folder_name> .
```

For instance, litellm pod deployement would be:

```bash
# First install
path/repo_name/litellm> helm install litellm .

# Upgrading
path/repo_name/litellm> helm install litellm .
```

In the case of ``values.yaml`` files:

```bash
# First install
path/repo_name/vllm-cpu> helm install vllm-cpu -f "values-qwen.yaml" .

# Upgrading
path/repo_name/vllm-cpu> helm install vllm-cpu -f "values-qwen.yaml" .
```

## Structure

#### Charts.yaml

We do not care.

#### values-....yaml

The idea is to have values based on the model and not the infra. So, for every model, tweak the values, mainly ``ressources`` and obvioulsy ``modelName``.

When adding a new model, make sure to 
