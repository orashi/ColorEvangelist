import numpy as np
import torch
import os
import sys
import functools
import torch.nn as nn
from torch.autograd import Variable
from torch.nn import init
import torch.nn.functional as F
import torchvision.models as M

I2V_PATH = '/opt/tomcat/webapps/ROOT/func/models/i2v.pth'


class ResNeXtBottleneck(nn.Module):
    def __init__(self, in_channels=256, out_channels=256, stride=1, cardinality=32, dilate=1):
        super(ResNeXtBottleneck, self).__init__()
        D = out_channels // 2
        self.out_channels = out_channels
        self.conv_reduce = nn.Conv2d(in_channels, D, kernel_size=1, stride=1, padding=0, bias=False)
        self.conv_conv = nn.Conv2d(D, D, kernel_size=2 + stride, stride=stride, padding=dilate, dilation=dilate,
                                   groups=cardinality,
                                   bias=False)
        self.conv_expand = nn.Conv2d(D, out_channels, kernel_size=1, stride=1, padding=0, bias=False)
        self.shortcut = nn.Sequential()
        if stride != 1:
            self.shortcut.add_module('shortcut',
                                     nn.AvgPool2d(2, stride=2))

    def forward(self, x):
        bottleneck = self.conv_reduce.forward(x)
        bottleneck = F.leaky_relu(bottleneck, 0.2, True)
        bottleneck = self.conv_conv.forward(bottleneck)
        bottleneck = F.leaky_relu(bottleneck, 0.2, True)
        bottleneck = self.conv_expand.forward(bottleneck)
        x = self.shortcut.forward(x)
        return x[:, :self.out_channels] + bottleneck


class def_netI(nn.Module):
    def __init__(self):
        super(def_netI, self).__init__()
        i2v_model = nn.Sequential(  # Sequential,
            nn.Conv2d(3, 64, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.MaxPool2d((2, 2), (2, 2), (0, 0), ceil_mode=True),
            nn.Conv2d(64, 128, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.MaxPool2d((2, 2), (2, 2), (0, 0), ceil_mode=True),
            nn.Conv2d(128, 256, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.Conv2d(256, 256, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.MaxPool2d((2, 2), (2, 2), (0, 0), ceil_mode=True),
            nn.Conv2d(256, 512, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.Conv2d(512, 512, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.MaxPool2d((2, 2), (2, 2), (0, 0), ceil_mode=True),
            nn.Conv2d(512, 512, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.Conv2d(512, 512, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.MaxPool2d((2, 2), (2, 2), (0, 0), ceil_mode=True),
            nn.Conv2d(512, 1024, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.Conv2d(1024, 1024, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.Conv2d(1024, 1024, (3, 3), (1, 1), (1, 1)),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Conv2d(1024, 1539, (3, 3), (1, 1), (1, 1)),
            nn.AvgPool2d((7, 7), (1, 1), (0, 0), ceil_mode=True),  # AvgPool2d,
        )
        i2v_model.load_state_dict(torch.load(I2V_PATH))
        i2v_model = nn.Sequential(
            *list(i2v_model.children())[:15]
        )
        self.model = i2v_model
        self.register_buffer('mean', torch.FloatTensor([164.76139251, 167.47864617, 181.13838569]).view(1, 3, 1, 1))

    def forward(self, images):
        images = F.avg_pool2d(images, 2, 2)
        images = images.mul(0.5).add(0.5).mul(255)
        return self.model(images.expand(1, 3, images.shape[2], images.shape[3]) - Variable(self.mean))


netI = def_netI().cuda()


class def_netG(nn.Module):
    def __init__(self, ngf=64):
        super(def_netG, self).__init__()

        self.toH = nn.Sequential(nn.Conv2d(4, ngf, kernel_size=7, stride=1, padding=3), nn.LeakyReLU(0.2, True))

        self.to0 = nn.Sequential(nn.Conv2d(1, ngf // 2, kernel_size=3, stride=1, padding=1),  # 512
                                 nn.LeakyReLU(0.2, True))
        self.to1 = nn.Sequential(nn.Conv2d(ngf // 2, ngf, kernel_size=4, stride=2, padding=1),  # 256
                                 nn.LeakyReLU(0.2, True))
        self.to2 = nn.Sequential(nn.Conv2d(ngf, ngf * 2, kernel_size=4, stride=2, padding=1),  # 128
                                 nn.LeakyReLU(0.2, True))
        self.to3 = nn.Sequential(nn.Conv2d(ngf * 4, ngf * 4, kernel_size=4, stride=2, padding=1),  # 64
                                 nn.LeakyReLU(0.2, True))
        self.to4 = nn.Sequential(nn.Conv2d(ngf * 4, ngf * 8, kernel_size=4, stride=2, padding=1),  # 32
                                 nn.LeakyReLU(0.2, True))

        tunnel4 = nn.Sequential(*[ResNeXtBottleneck(ngf * 8, ngf * 8, cardinality=32, dilate=1) for _ in range(20)])

        self.tunnel4 = nn.Sequential(nn.Conv2d(ngf * 8 + 512, ngf * 8, kernel_size=3, stride=1, padding=1),
                                     nn.LeakyReLU(0.2, True),
                                     tunnel4,
                                     nn.Conv2d(ngf * 8, ngf * 4 * 4, kernel_size=3, stride=1, padding=1),
                                     nn.PixelShuffle(2),
                                     nn.LeakyReLU(0.2, True)
                                     )  # 64

        depth = 2
        tunnel = [ResNeXtBottleneck(ngf * 4, ngf * 4, cardinality=32, dilate=1) for _ in range(depth)]
        tunnel += [ResNeXtBottleneck(ngf * 4, ngf * 4, cardinality=32, dilate=2) for _ in range(depth)]
        tunnel += [ResNeXtBottleneck(ngf * 4, ngf * 4, cardinality=32, dilate=4) for _ in range(depth)]
        tunnel += [ResNeXtBottleneck(ngf * 4, ngf * 4, cardinality=32, dilate=2),
                   ResNeXtBottleneck(ngf * 4, ngf * 4, cardinality=32, dilate=1)]
        tunnel3 = nn.Sequential(*tunnel)

        self.tunnel3 = nn.Sequential(nn.Conv2d(ngf * 8, ngf * 4, kernel_size=3, stride=1, padding=1),
                                     nn.LeakyReLU(0.2, True),
                                     tunnel3,
                                     nn.Conv2d(ngf * 4, ngf * 2 * 4, kernel_size=3, stride=1, padding=1),
                                     nn.PixelShuffle(2),
                                     nn.LeakyReLU(0.2, True)
                                     )  # 128

        tunnel = [ResNeXtBottleneck(ngf * 2, ngf * 2, cardinality=32, dilate=1) for _ in range(depth)]
        tunnel += [ResNeXtBottleneck(ngf * 2, ngf * 2, cardinality=32, dilate=2) for _ in range(depth)]
        tunnel += [ResNeXtBottleneck(ngf * 2, ngf * 2, cardinality=32, dilate=4) for _ in range(depth)]
        tunnel += [ResNeXtBottleneck(ngf * 2, ngf * 2, cardinality=32, dilate=2),
                   ResNeXtBottleneck(ngf * 2, ngf * 2, cardinality=32, dilate=1)]
        tunnel2 = nn.Sequential(*tunnel)

        self.tunnel2 = nn.Sequential(nn.Conv2d(ngf * 4, ngf * 2, kernel_size=3, stride=1, padding=1),
                                     nn.LeakyReLU(0.2, True),
                                     tunnel2
                                     )

        self.up2 = nn.Sequential(
            nn.Conv2d(ngf * 2, ngf * 4, kernel_size=3, stride=1, padding=1),
            nn.PixelShuffle(2),
            nn.LeakyReLU(0.2, True)
        )  # 256

        tunnel = [ResNeXtBottleneck(ngf, ngf, cardinality=16, dilate=1)]
        tunnel += [ResNeXtBottleneck(ngf, ngf, cardinality=16, dilate=2)]
        tunnel += [ResNeXtBottleneck(ngf, ngf, cardinality=16, dilate=4)]
        tunnel += [ResNeXtBottleneck(ngf, ngf, cardinality=16, dilate=2),
                   ResNeXtBottleneck(ngf, ngf, cardinality=16, dilate=1)]
        tunnel1 = nn.Sequential(*tunnel)

        self.tunnel1 = nn.Sequential(nn.Conv2d(ngf * 2, ngf, kernel_size=3, stride=1, padding=1),
                                     nn.LeakyReLU(0.2, True),
                                     tunnel1
                                     )

        self.up1 = nn.Sequential(
            nn.Conv2d(ngf, ngf * 2, kernel_size=3, stride=1, padding=1),
            nn.PixelShuffle(2),
            nn.LeakyReLU(0.2, True)
        )  # 512

        self.exit0 = nn.Conv2d(ngf, 3, kernel_size=3, stride=1, padding=1)
        self.exit1 = nn.Conv2d(ngf, 3, kernel_size=3, stride=1, padding=1)
        self.exit2 = nn.Conv2d(ngf * 2, 3, kernel_size=3, stride=1, padding=1)

    def forward(self, sketch, hint, noise, stage=0):
        sketch_feat = netI(sketch)

        hint = self.toH(hint)
        v = torch.cat([hint, noise.expand_as(hint)], 1)

        x0 = self.to0(sketch)
        x1 = self.to1(x0)
        x2 = self.to2(x1)
        x3 = self.to3(torch.cat([x2, v], 1))
        x4 = self.to4(x3)

        x = self.tunnel4(torch.cat([x4, sketch_feat], 1))
        x = self.tunnel3(torch.cat([x, x3.detach()], 1))
        x = self.tunnel2(torch.cat([x, x2.detach()], 1))

        if stage == 2:
            x = F.tanh(self.exit2(x))
        elif stage == 1:
            x = self.up2(x)
            x = self.tunnel1(torch.cat([x, x1.detach()], 1))
            x = F.tanh(self.exit1(x))
        else:
            x = self.up2(x)
            x = self.tunnel1(torch.cat([x, x1.detach()], 1))
            x = self.up1(x)
            x = F.tanh(self.exit0(torch.cat([x, x0.detach()], 1)))

        return x

