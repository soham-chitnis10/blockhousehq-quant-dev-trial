# blockhousehq-quant-dev-trial


## Architecture


## Install Docker on AWS EC2 Instance with AMI Ubuntu

```bash
wget https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/containerd.io_1.7.27-1_amd64.deb https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce-cli_28.2.2-1~ubuntu.24.04~noble_amd64.deb https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce_28.2.2-1~ubuntu.24.04~noble_amd64.deb https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-buildx-plugin_0.24.0-1~ubuntu.24.04~noble_amd64.deb https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-compose-plugin_2.36.2-1~ubuntu.24.04~noble_amd64.deb
```

```bash 
sudo dpkg -i containerd.io_1.7.27-1_amd64.deb docker-buildx-plugin_0.24.0-1~ubuntu.24.04~noble_amd64.deb docker-ce-cli_28.2.2-1~ubuntu.24.04~noble_amd64.deb docker-ce_28.2.2-1~ubuntu.24.04~noble_amd64.deb docker-compose-plugin_2.36.2-1~ubuntu.24.04~noble_amd64.deb
```

## Starting Docker Engine

`sudo service docker start`

## Build and start the container

`sudo docker compose up -d`

Note: You must be the folder containing `docker-compose.yml` file.

## To run the docker in interactive mode with bash

```sudo docker exec -it kafka bash```

Execute the above command in both terminals of EC2.

## Install dependenices and download file

Now, install the dependencies 

```bash
cd /blockhousehq-quant-dev-trial
pip install -r requirements.txt
pip install gdown
```

Download the file using gdown by using identifier of the file. 

## Simulate market data

### Run the producer

Now, in one terminal run the following command

```bash
python kafka_producer.py
```

### Run the Backtest

Now, in the another terminal run the following command

```bash
python backtest.py
```

[Video]()