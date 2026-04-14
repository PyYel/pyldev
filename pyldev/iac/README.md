# Infra as Code


## AWS CDK

You can use the ``cdk.bat`` tool to quickly run the CDK CLI+libs and generate ``cdk.out`` schemas.
This script a project folder with structure:

```bash
# Minimum structure requirements
root/
├── infrastructure/
│   ├── cdk/
│   │   ├── cdk.bat
│   │   ├── cdk.json
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── stacks/     # Your AWS CDK IaC
│   │   │   └── ...
│   │   ├── constructs/
│   │   │   └── ...
│   │   └── cdk.out/    # Generated output
│   │
│   └── ...
│
└── ...
```

A realistic organization would look like: 

```bash
# Example structure
root/
├── infrastructure/
│   ├── cdk/
│   │   ├── cdk.bat
│   │   ├── cdk.json
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   ├── stacks/     # Your AWS CDK IaC
│   │   │   ├── vpc_stack.py
│   │   │   ├── ec2_stack.py
│   │   │   └── ...
│   │   ├── constructs/
│   │   │   └── ...
│   │   └── cdk.out/    # Generated output
│   │
│   └── terraform/      # Other infra etc..
│       └── ...
│
├── backend/
│   ├── lambda/         # Source code
│   │   ├── user_service/
│   │   │   ├── index.py
│   │   │   ├── requirements.txt
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── servers/
│   │   ├── processing/
│   │   │   ├── Dockerfile
│   │   │   ├── src/
│   │   │   └── requirements.txt
│   │   └── ...
│   │
│   └── ...
│
├── README.md
└── ...
```

## Terraform


