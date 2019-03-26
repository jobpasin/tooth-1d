FROM tensorflow/tensorflow:1.12.0-gpu-py3

RUN apt-get update && apt-get install -y git

# RUN apt-get install vim -y

# RUN pip install --upgrade pip

RUN pip install h5py scikit-optimize

RUN git clone https://github.com/jobpasin/tooth-2d

# RUN export CUDA_VISIBLE_DEVICES=1

RUN printenv

WORKDIR tooth-2d

# CMD bash

CMD python3 mnist.py tooth_workspace.config