import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class Relu:
    def __init__(self):
        self.mask = None

    def forward(self,x):
        self.mask = (x <= 0)
        out = x.copy()
        out[self.mask] = 0
        return out

    def backward(self,dout):
        dout[self.mask] = 0
        dx = dout
        return dx

class AddLayer:
    def __init__(self):
        pass

    def forward(self,x,y):
        out = x + y
        return out

    def backward(self,dout):
        dx = dout*1
        dy = dout*1
        return dx,dy

class MulLayer:
    def __init__(self):
        self.x = None
        self.y = None

    def forward(self,x,y):
        self.x = x
        self.y = y
        out = x*y
        return out

    def backward(self,dout):
        dx = dout*self.y
        dy = dout*self.x
        return dx,dy
    
