#!/bin/bash

IPTS="./ipts.py"

CONDA="/opt/anaconda/bin/activate"
if [ ! -f $CONDA ]; then
	CONDA="$HOME/miniconda3/bin/activate"
fi

#echo $IPTS
#echo $CONDA

source "${CONDA}" shiver

python $IPTS

