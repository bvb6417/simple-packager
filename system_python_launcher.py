from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
from typing import Callable
import zipfile
import zlib


GUI_STUB_B64 = (
    "eNrtPAt0W8WVI9my5V8kkhicH3lQmco0Tu1AsjEkxbJleE7kRImdT0mIrchPtkCWhPQUOxCoHdk0jxeBF1r62R5qemLabtk221JI"
    "srRV4gQ7pbROysdZKJsSWp5rsjjQUpOSvL133siW5EC3e3rO7jmbd85w5965c+fOnTt37owV6m7vJRmEkEwoqkrIAaJ9leSvf51Q"
    "Ziw8NIM8nfPiNQd0jhevaWj1hrlgKNAScrVxbpffHxC57QIXivg5r5+zr63n2gLNwuKCglwLk+GsIaT5gRxindl6Z0LuOFmsz9Pr"
    "SwkHyLVQ9IQMzwJo1lTTEVbXa3rjZ0AEv/3aZF5Zh81NwMppdHNCujkNT6nSSXXnJuFO0E+fhPcB/gk24WyEWC9BH9+t6ftx32JR"
    "6BBRl6uZQhyZmlxCNiFNi5tdootNk5QxmZZUPli7+OKQxjiSxRbTCOW6aXyVi4MaH52jk425+BJ8HRpfPvI1Mb4ll+DbHg5TM+Ii"
    "BT/Wb+KLvZo8amt0pHwoyy4hT/SFJ9eol8236lLzFXwBN1ubPsZnn8ZXRS5/Kd+Ax7PYtLCb1k0LK4ltk22jbYOtYcOmjfV89J3N"
    "B9DHhBZeJrwcNPLygnlLCVRXzodVGZvp6eUrnjd1/wB4DioQRtRXy+PjvOlfb4i8XVN+lpeXXriREDkrOqEzda/KwGpP3NSNyzho"
    "2N1ICDpJTc9ZU3dMj1INV9+IgPA9cTG/pjx+CBex/Lg6rLw8lxCHbNgGfeSCVvivQwLGwo1QUw4akXgzVHuOm7rPQh+5sASxk6bu"
    "BSg3enTzlm2Nd9i22u6wbbM1DtB5/gTHHv28qqqmheAng1mIKz/JRwUKngc91MKyECKFc1CpWMHJi6rKS3rl6/OAz1BI9f3lDajf"
    "IJ0HoL8CdBI5mYwUAuLpWl53e+RzvNu5gtcNdy3H0Bf5rOlZZ5Gn63weWChXj0zn8/SROdEDuCQzdpjt8p4JaoQamNyXD/eCrFqQ"
    "JRWs3gb+LYP14qaeRhjlINX/N2AnZc9cqvc54JNnSmYlqOGHE/hEDhgnbtrzJ023z8M2ji6H8XfqKP5diqum7tspXrjzBmqT7QCU"
    "L8+lXXuWaqw/BZojZhi8Ay1UOERBwXEAMpHsFgdwbL0B1TTyMUSBxim3z0ERHfc63MXfBE5bzGHR8e7j/OHfZihPoqY9cV46Jm6p"
    "6XkL/EwEFtNDj4Cmtp/hDMcWeuh6rZIb1Ik6aVy5AbrUxm7T1VV8JHprpcFVskOdUIQ5qJhI9A7pnOJMSD28SrJfmIgMoMcQ5R+L"
    "IKKASiuUh4FbhsroiQuqqskvj/NfzBj1TuIH0RWV+4Fx9BvgCKti9t+hbVaCrfhBunvARAsRk0rjW4HVDazKRQN6FnYdLbyAnkYO"
    "qIig3IPgeqqyFyV+BV1LLmiC7sq8GUDYAYRohzjD9EA+1Oxyr8J84CT4wOgE9l6I+vzyKnCFw8qmmTATTU/Ys1Ywe3F5wvmU6z9S"
    "1d5e2ARWcPxEu4G246fkprSPPopWmfpgPXNQ47foRqkkA72pH40SINGGS2zW8fI6My+9wFccCZfxPScPogq8yX6Cl17hdSchWIT+"
    "xMt5yvNFaKgjYOSek2I+L83ipbD5AN0roMeWbQP1fNc7XBZ1rts/Q8ghzFFs0nEenIVTC78CW9B20Ext4hnstlyNhxzy/uIz6IEN"
    "yJMBh08v33UUpWwZ0NSUXjlEx5BeUOwwn564dERcwMvVENfyHLFKHa+LO6Rqo0e6UecZtOtg3aRhplBSTLSWn62VXjp0LZP0BJVk"
    "6v4j4B6bnGnxIDaEWHRia8TAq8fGWqB6bWSDI+Yr1ZWfPbSVdj2leFjXg4irxxwVZ0NnmNxTSi1r/AZO8+yYZbJXGWuI0l4v8j1n"
    "I2dspmdnW8aGaqNH9aPt0A7LNnI9LO4dV9I+YOta6aiy9iL2FOtwyqtj+RbsHVv6A2CEmfMZGbw0+P4+R4Yb7JHhkNxGT9VgZhPu"
    "nbOR7yf00uyhRdPRfhAIi5hEGmBm6npnHPU++ZNsAD/D01hqsDjVwm/4tBVywm5UC9f4Uebz0oe87rjy3SvZNh2IzCx/je/5QKzg"
    "pXNq4RPQZWxx+XGbNAHzUAvv9mEAEbNjm9SK4RC42ymdqjRDZ/XFyI/HjkHHiBGIo99EhWO7LJvL4wfRQd7/HsUgUA2U4LAfKp/W"
    "7DH/EEc0wssXKCGPl/4d0Wy6L32Wzbbn0G+g5SZ7RbPFeX9TogcvQavyOO0Wyaa8Y1eukmf/Htpq1aPKsQtMwtgROpeX79LW8Md4"
    "fkijyr8A1KJRLnDSHTD6BhoufnAOno1wuHRb9kCtlWh2C/Kx5yx7tdlIr7J5OWIaU3m8HI6oBgvPS39wQGSrhDMUg+5y/E/ZoN2C"
    "makRIIcDqYV/vhMnZZOORoxq4UxQTRqkWn6WaWliWmYX4jH9lvShqbsBnUt2WIKHMHyphTfepenVQIkgukET/dydGBEdlg5IGfZA"
    "Xf01ZVB/DXG2AbYleofmM6kRRS2+yYcBKJGTsHi14arJxOBaGufUYaDegtSYE9y1Ela8sOwq6kCRMzSYafEwEZ8KoxgaZH10QpUO"
    "ixU9x0VOGoqO6vjY/CN8yRAfE49MYHxTZ/HRMSNf8X7kT7CH7sfZUu8ePXOexu/yeErCROwQNuBcia44AilJPDI+1p/aLht+vpF6"
    "TtaAlmcYntmo5T2jLhDeizsF8yElYxZuF14u4ntei8wf/RLLxyCYiNXRN3Xi57TQFR3Qm57NgHDC7XhLOhE9p8PIAgF27HdJ4yar"
    "8Gy1HjtFFeRcuONdFkJv9BLygd2yVWc7iBm4mGU3PeuwNMEpdCeEg1ppBHTpOoqabRkt+QinztYjtuC7cI0YO8DWK3o+Q8yDIJ7N"
    "7D36b7kp4yfsbzhTglmFXswapKl59LxenBU9rxNvZQHWtLCTya9YhGDpEgQV74v/oZ1rcgYuvh7WPTpA1+cs65g49+gqrUwd3dNb"
    "Hh+Yfl51mEpES6WpZJfFaTeV2C1N0Yos0xdfhA4yOESh79Mgz525G7I09fSUXs7rUI27je/ZTWYb957JvLMI/nO3WUsNMq4gBFqu"
    "gI1WK50DA75numKXxQphDiqihQO5CghQVpvAvU1WGL88brJSDaygAejfAZOB83bB8WKw72NT485Bez8whY9C+2iYnceA10L7qHsK"
    "vwLxenoILHBj/TZ0NPZd0h7LMT3bDIcZnQpGjiaH5LC0YizZjLHDqljMNMVrQxtAxtEzA20hWqza5LOwFWPm4VpIyazQqNxrxpyk"
    "Vzsynbx76bIG2AcfwCCmh67SskdrA41wfDRe5EmsmEMmjoqB0Cxedhrl9cZa3TCgpt0PYgIYPawDXqut4lxkBMNTXy47MAZN3b/X"
    "ctmX61HN+c/wh89k8Drg6uBYmvOjPFjdTfk2eqHhY/lm4P52PUsXeMlRVKQWNnqoQFP3fYQmhPaY86Pom38RjTFnPPrmzyIzo4YA"
    "dAEtjjoheGG+FJ3Q2w7g/fpAJtEiHmc32eO83ABRN2NBTT1uJjh/V0OAqjerhX8UMBpEnlELvyXQbPlRWE3piCJe1Nav/IPRa2iI"
    "NeRS5QpuLka9jQ7ZXlSkrLlIj/bsYmpu5RZAe1PjzYbEBU4zPM/HfJZKeemP16PxxSv4mGAEzRNXoTsGBg2PrdfikXICEj3+q3ws"
    "sxPKMRONNqfHlbn5uCrFbur9C3wISo4OGtzrCQsI4PG8ZNiyHj3nNF8ywkcnsu9/DP6bZ3q4ByTLGXhjCOO9rDoTq61YrTfC7jf1"
    "nKAXtIF8SPXPwaxsP8VTxVFxJrRr1IluGz1vNHW/qsOAYTb13AvckOrUEFvX6Tju7574ziy+AJ+uHCXDDt1QDbpDzUSkiF+Jr1mm"
    "h+9A+StJJ1h37zo9Jon3TTjgSGuG49Z2QHP380gYK9AUgbHD99ghQbLLs+TVmTbTM8O1uvPR81ydnOuILaowdZ9CSz+AGy56vtLU"
    "8zYoVyvXEE0BphhVIgd9SXpNNzkqylf+8BGObJwa+W4YGWf8IK6/bJixDg6C18Aex930rvUQf5FeQlj8lQ3nnJivjWiXP7EAdoq5"
    "DjIRmTeqr0afB+ccsN68dAiYdp0czb/I7rfyLLg79PwnoYsgDebdazT1BNGbQKXR2ykXjS82edK4YNsCHlNTgmvC5wylmni+o2Lc"
    "9PAF1AmvMl+gTBVDpof+QKbMfOEvONnMqcl2gzeNfilpPNMzkwN2a4uppi/mlbCYaPOHe6lPTnSa9j6QNMbX6Bi6qTE4HKOMjoGG"
    "NUWzYLEdcmnvp7RO1M73ZuJBIldPOHTvZmRDugYjKWuS1aUJYZ62NsOjbm3r2a/FC1/NBI0pPzuPTwJ2DO4FW6ChTlKU752nfG9d"
    "A+3fPD8VeBP3qeg7m2ENl66lkcZjmv1rsRhOkW4LWgNiLkfPZwy8VlNJg6XsPTxRKtVhvKBtHvD08lLBh2tgevY87ZqGm5zj5Stk"
    "PURW6XDXb8F6XNeH1dW3cabuh0HmyscIibfftlIGsMNlgHPjluhETvtdEMzxbTX9nCs/qaWjR3OpqXWm7s/ptKDYo9Oi9tfXUFys"
    "0S4D3BZePT0VglbCjRcCaD9U229YCfurM/LCAVVLo7gtA70fVGXCrm8BwphC411ca5jsD6PHxRdXLgAQ+UfQBhdDWTapDd6GaIgO"
    "gQjaqA6PPT41fkL/zESPnkpgpLmT1jAGUW70TnXynn/yYB6SX8rR+MXrqfTZKD2PSh9dqSbtPyoEiNZJqbT7l1Hq7EkaVboLaSR1"
    "9DagKUNgltG3L1LfmLxVco5YcaAOHe+3aqG/kQbbW+pwsq+Jy3i59EeUtNLXqOWFcp76Mtyc1FfxnlQAJ0oOvcdC9g6J8RYzJpGv"
    "gyhqXJpm82qxE/qywWTDmAN3uPQruJlHctkqwJF2qIgk3pJychL3MfEGXgrCBX/pL6GTtJzeEV7YRr3hGw4Mdud4acEjtFYNZ5wC"
    "TWNP0VUf+3ba+6KWD8oGnzb8C5EZifujlh/DIF5NpFrYSocoqEAcEvZ/KD85Ni9FnJ0p+HNxHqQesq5ihJdt5sgYvipczUtVZqXO"
    "yGQ1bCMkaSQgGn67GtT8TZp+1DqQnJq6f4guXAaSHLLhp6tpKO7+KX25fGq1dmImHizAfSf9A/LhyNuyIUY7iL9R5sMyj70yNYZs"
    "CNGmiEc2tEINXC7yLCx1w2ptqYsSeR5sLlhHZW82pUcgby9wIs+goXi1dvIOGj7Famrh0jvApXz4oHRXqmLKP0HsG3t06vyIFeSs"
    "xh43Y48ydVqAmh6vMHs/djX0MUM+x/B+De/tfe1Maj4J96OuirrbIybevW4FrzvRVYHPnKIxkd9j+86iPL3pS3H6Dsu7bcB2GG4f"
    "tiwosz0Y9GN2XZG4xBbjIZLmS46YY8ia0N8uV8IRfcQhHQ4ZM3i4CPw8lIdJoaNiKHIGktvEGw0v/UpxGuieNrbPAI0fXcBeYMXZ"
    "cLpKI4lHi8T9wd0Kehzruo/+RSryuqfrPtAy8hIkG7M90fuywHBbDUXi0fIPNH7tBOfxlDilvJtJV/u7wJzFTuCK50Ovjz0G9pIL"
    "5yzQpn0TmMXscFetgKTWpj3/TtnFY+vqwAHfhfSmcjZfcqI2ZidFNYBkoUnEG20xJ1hj9iNgjWHrlD9p9jjskI6APeAmXHEi9FSy"
    "PWDmX5tP38no67Mp5fVZzJGG2Pw9bHjTs3yWRkzk44bPz6f62zQBtSDAoTvSdVOa/l33YP9xWMgqWMiqxELqi8RFCdUh1R62Mv4P"
    "Kj/NiTm4rX/C4zUcVOYrjkQUUDnl/gb6n5qHYXpSfx79hblVDi8NDzD90at4k30YSVMSwP5fm/e32L8GLQD2h3Vw4iSO18YazEXi"
    "q7aYTcXcGOx/JMX+VZr942D/KrD/4VA+Hz1ira04Qe0vV1n+PHxYWZgYxyEvyJlHrz0w4s2oUZ27ekWdbiSh0QwHmn/KAkyvUZvc"
    "2au9Qb0BKjqzEvqd1PQ7XhOrUteCfmtiDan6rQL9huqkoVCOHRR0VMThckUVPBl5E9TA4TBP0o2M5eJ9hq7FbHCrzBp80pKd+RAC"
    "X+05/oXf2WU+v053CjtM7fd1Tsiu6d3QYSkKzeG7RikWzSF8Ka3R1va3+ZLDSNz8+bQHZG27luGbsfSKQxpUXtOeveAeiRdKGY60"
    "XRZOwb/WwI4twyPqEv0r8WUvmBBitwTx+tqBXZcrD15SoE8TWJkucMPkvekp+qSWkLmXYg58IPOB0KUE73UfJgn1wV0fX9a0R6vj"
    "OmWmNgJPg0zSe7phFKLFJAH/njOHvm1pJHr+sIu48gMasAv3FOHj9wjeuwu0u+F10OUg5sQ0Bl9Cf6tdepHqPYCB8Fd4MF3Q0WM9"
    "ekpVvo3C8Q/SMpGylS6iva1JWQrN9bCawcP1NygblY/I1LmJ81CL79mMmWc6TPibWnw9o38ynOK/ZxOT89+Eu/9G+OCm1PHe26jR"
    "E/DkxtT2H6bhIcb3yXCKf0kaPpPx6RPjbtDgmwyeZPAIgz9k8FsMPsLgbgZDDG5ncD2DVQwuYfBaBmcyqGfwDyn6jc77fUoKcPkv"
    "4v+/vs5b2e9p2KeyL4FfTKqTS/yERU1rN38mVZ4lfby09t40fDgND96dil/+/r7f9S33by9bf+X208LLvs82fGf9X3b9x/0jj++T"
    "OeIkO4lIWkmA+Im+LJfkkj/L/Dppy7E9qW356o5t/o7frOVIMIm6mAikAwpH3rujb72wDuViPxtpIDyTt4l4gbMZ+NtJGDjnfPld"
    "+cwaXcdctZj4SAS0u+kLV2xN9JySTchWspX+vGj6eH/r1zT3r/hXr9ZuZHBXUIP7b/3v+aUt1BJpE/wi1xxoc3n9nBAKBUKc1b62"
    "zla7pmSqOez1t0R8rpBX3MlZ62tvgzb6rd0hhDy+QDsXcvlbhET3tRtr1t/qWLuphDhdIdHr8nG+QDjMBTwgp8Xv9XjdLr9b4KxO"
    "x9r6eiqpISB+LFfDJBfwtQpcSAhHfCLnDXNiIMCF21w+H9ToD/mEIDSCvkIzZ92wxp7QYoP/Ln+gnc2Oymlsc4mtgFpLbuKKw/jr"
    "v+KwtbhlEVfcUsJx1pAg7nD5VgKSS8jmU6qaD2XfiKouArgCigPKfCh1YJf20vZlN+KPCEVvm8B5XF5fJCTcpP1Iz9bcDBqFueIg"
    "1+oKc/4A521ztQilYcEtegN+wnEbvSEx4vKtiwihnbQz6O4BIxY3c9t3ikKYc4mca1LK5G/tEv2coYAIshI9271iK+cONAtcWUdx"
    "B/Il5h4MC5HmAEd/h+bCsfGHkGLAHfBxsIZhJBQ3L86dlP/x/bZ70R/uEZL5UVsgT2cG7WHugYiI60qdZBEnukItggiWg6ZF3E6v"
    "4GtGBBaEA6tHQHAwIdj8hqqml2YGh1n98TemYnxiFTRHLG7OTfP3srLUfVGZhjdN3zef2D6N35aKc2ny+9Lwsu5UvDUN7w2m4h1p"
    "uJiGB9Pw4TS8Mg3n0/A9afPpTcO/mob3peGdafKcaXg8Hb8mFR9Pi3dNafy3VVffxFk7li9rXHZjaTAQ9nbAVmotDQk7yhZxVREv"
    "xIXtOznYlbdtKkW0mf7e907YISVc+dLFSxaXTc8PaI6w+JPzjL81XlfOvZwX/F0+uJ3rzNpves0Afz6LEPzND/7e+iyU+VAfB1gw"
    "m5AVyAOwEMpWqHMAF0FpgnoZwHIozVCvBPgVKK1NGnwbitikQWsh+HCTBtddScjeJg1G4Y7bB/U+gP8O5Wmonwa4Hm66z0G9CeAX"
    "oAxBvRNgxVxCftFE/YBsgDLSRH2D/BrK69gX4Bn8MWQT9XmizCPkHawDfB9KJv6Iej4h26AYod4E8MgCQmZDfRjg9mtgflAPAvw+"
    "lOVQ3w/wOSiVLrqvyH2fIsQO9U6A4/i3JZcGXZD0bsW+AHXFYAeomwHqrwM7QJ0DuBjKLqiXAfwclG6oVwKshrIX6vhjg11QelE+"
    "wGEoX3JpcNunIU6gzgBPQ/mOS4NXWQl5CuUDfBTKfqj3AXwFytPIA9AL5/wB1A3gsuthPigf4I+gxHFeADM/A7Z10VyetEAZQX6A"
    "HVAUF83hiQzlHRfN38kRKOMumruTzy4iZMKl/YbcAMW4/fIW+7/8YQzVmXOI+Vv5ZXlNucEcpzGeNZx5Wj9OSE6mjmRWwdou0vhe"
    "gjjw9izN9xGmt/8RaNmztXaEOpJUsjJIVpW+TAd7UGfMIEbdUaIrS6PnZ5P8KmNZdlNW0ODMjOuHgVaQTQp0V5OsMkNTZjDDqY8D"
    "jY2b0pck5M7U5JJLtF+ZQ67ck0XMHQaS15pJst5MakPe7QzPziTZj2SU6Zt0QV1hbk1hhnk3s048e9hwOmNc56Q6fIv1NeiJYYmu"
    "TJebRXKXTGlK5SxhcpJ1SfAn5pGAyfYyGoixKrMso0kf1DnT2pILjrGejYH1EKtj/92X6J8Y+xLyL3///77xzqn6gT3av1Pa0zVF"
    "+wXQ9kThvEmiGSXAgTaURFsEtCGgjSTRGoA2EsW/hE/RdgFNwV8u756ivS7hjz/gXEmizX4QcKDtT6JVAm0/0IaTaK1AGwba6SRa"
    "B9BOd3/MfBn9IoPmHg1aGaxkcD2DrQx2MPgQg30MPsfgSwyeZvAig1kPsPkweB2Dyx5I1cuRhm9luI/BHQzez+CeNP5H0vDvpOHP"
    "MfylNPobDH+HwfMMGr+owZkMXs/gcgYrGXQyGGRwF4MPMvgUg08z+NwXU8d/nuEjDCoMfsCgeU8q/yKGL2OwMq19VRretOfy+l9e"
    "/6T7Nan2BcIC7/I3+wTyF1IdElyi4AwF3EI4vAn8QGcXfIIoVIe8otft8tWzd6Q1uhq/KITSyWRCd5sgVgfa2kCgw+sXNhGXHig1"
    "HV6gNicEEyIh1eEKizXaE9njiNcFmiM+4VavT1jjaoOuREVqvegKiZFgrd8T2ES+klHr9+ILn/eeaTr9KcMhuHZMI5PsTEcA8FtD"
    "gkC+bqgXxA3+Vjrf5poOtxBEJhgTZkP+2VDvE4Qg+aWhwReGoTfi6xC5aEh9+0I3Tn5Fg8wva5PLK94aCNV7/S0+Ye12fAAgetLY"
    "GGxsbBf8O7whUKSINIYFsdEvtDfiP/slcwhoRf+V5lziQeXIPNLGKPMJLASt5pJGd8Dv8baIrUBqxocuWCmgorBIWAixl0W4kwKt"
    "ujEcFNz4ltmozRHot2S2CW3u4E78V8FUo0ZXqAXGyGZYO6A7qETU1t3W7POTq2BUARYNdWPjR0JCY7u3WWik7GQh0ENiI3gLsllI"
    "I4V2bY6uYLBR3BkUyD+QRu/kgmndmTnwmRf2j9YOxm8jFVP1RoGs0iR5/Tugb3Nj0BUCn4C2qXmBb20PhESymWiaegi+47p8mL3B"
    "HFE7b2B7oyfidyfWwg2eiaYnGRru0bBMtKbY7A1oDP7GHZ5gyOsXPWTmtJZwO2si3yFhMeQTwMO+hzW/uy1I4qTdHaa0PJK0DRoC"
    "NjAaeHS7vg7839UiVAU6NrF//Pv3KKtr1q+pcdywZHGzz0fjK9BcQW9pW7i03esvBVuUJtm91FdeWl5axpitndNLWt9WwRVM6bRi"
    "Oo/mmamiiXM6H/prCldzp1bS+MDMO8C7UgV2dP7PS5p89nSbKn9v5/SS1o+6Q3KvPuBJlGm84CstaTZ5Gvjq+RpHYrmGAN9QX7N+"
    "avUuf5e/y9//ylcGsZMmtM6+YF9nX29fXx/+jxLwfwVBnuCesD5R9sTyJ5z7mvYF93Xu693Xt2//vvi+4X2n943vI/3mfq6/rL+y"
    "39nf1B/s7+zv7e/r398f7x/uP90/3k+ebH1y/5MHnrxs5P+7338B7Xjl9w=="
)
CONSOLE_STUB_B64 = (
    "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"
    "3/3+HZ6WkU0="
)

PROJECT_SETTINGS_FILENAME = "py简洁打包配置.json"
PROJECT_SETTINGS_DIRECTORY = "项目打包配置"

DEFAULT_SKIP_DIRS = {
    PROJECT_SETTINGS_DIRECTORY,
    ".git",
    ".idea",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".tox",
    ".uv-packager",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "env",
    "node_modules",
    "venv",
}

BOOTSTRAP_SOURCE = r'''import ctypes
from ctypes import wintypes
import importlib.machinery
import json
import os
import re
import runpy
import shutil
import sys
import threading
import traceback
import zipfile


CONFIG_MEMBER = "__launcher__/config.json"


def show_error(title, message, console):
    if console:
        try:
            sys.stderr.write(message + "\n")
        except Exception:
            pass
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        pass


def install_taskbar_icon(archive_path, title):
    """Use the launcher EXE icon for windows created by this Python process."""
    if os.name != "nt":
        return lambda: None

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    set_app_id = shell32.SetCurrentProcessExplicitAppUserModelID
    set_app_id.argtypes = [ctypes.c_wchar_p]
    set_app_id.restype = ctypes.c_long
    app_id = "PySimplePackager." + safe_cache_component(title)[:96]
    set_app_id(app_id)

    large = ctypes.c_void_p()
    small = ctypes.c_void_p()
    extract_icon = shell32.ExtractIconExW
    extract_icon.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        wintypes.UINT,
    ]
    extract_icon.restype = wintypes.UINT
    if not extract_icon(archive_path, 0, ctypes.byref(large), ctypes.byref(small), 1):
        return lambda: None

    large_handle = large.value or small.value
    small_handle = small.value or large.value
    if not large_handle and not small_handle:
        return lambda: None

    get_window_pid = user32.GetWindowThreadProcessId
    get_window_pid.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_window_pid.restype = wintypes.DWORD
    is_window = user32.IsWindow
    is_window.argtypes = [wintypes.HWND]
    is_window.restype = wintypes.BOOL
    is_window_visible = user32.IsWindowVisible
    is_window_visible.argtypes = [wintypes.HWND]
    is_window_visible.restype = wintypes.BOOL
    get_window = user32.GetWindow
    get_window.argtypes = [wintypes.HWND, wintypes.UINT]
    get_window.restype = wintypes.HWND
    get_window_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
    get_window_long.restype = ctypes.c_ssize_t
    get_class_long = getattr(user32, "GetClassLongPtrW", user32.GetClassLongW)
    get_class_long.argtypes = [wintypes.HWND, ctypes.c_int]
    get_class_long.restype = ctypes.c_void_p
    set_class_long = getattr(user32, "SetClassLongPtrW", user32.SetClassLongW)
    set_class_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    set_class_long.restype = ctypes.c_void_p
    enum_windows = user32.EnumWindows
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    enum_windows.argtypes = [enum_proc_type, wintypes.LPARAM]
    enum_windows.restype = wintypes.BOOL
    destroy_icon = user32.DestroyIcon
    destroy_icon.argtypes = [ctypes.c_void_p]
    destroy_icon.restype = wintypes.BOOL

    process_id = os.getpid()
    stop_event = threading.Event()
    applied_windows = set()

    def apply_icon():
        if applied_windows:
            applied_windows.intersection_update(
                handle for handle in applied_windows if is_window(handle)
            )

        def callback(hwnd, _lparam):
            owner_pid = wintypes.DWORD()
            get_window_pid(hwnd, ctypes.byref(owner_pid))
            if owner_pid.value != process_id:
                return True
            if hwnd in applied_windows or not is_window_visible(hwnd):
                return True
            ex_style = get_window_long(hwnd, -20)
            # Skip floating tool/popup windows; target top-level taskbar windows.
            if ex_style & 0x00000080:
                return True
            if get_window(hwnd, 4) and not (ex_style & 0x00040000):
                return True
            # Use class icons (GCLP_HICON / GCLP_HICONSM) instead of WM_SETICON:
            # DefWindowProc handles WM_SETICON via WM_NCUAHDRAWCAPTION, which paints
            # a classic OS title bar over custom-chrome (WM_NCCALCSIZE) windows.
            if large_handle and get_class_long(hwnd, -14) != large_handle:
                set_class_long(hwnd, -14, large_handle)
            if small_handle and get_class_long(hwnd, -34) != small_handle:
                set_class_long(hwnd, -34, small_handle)
            applied_windows.add(hwnd)
            return True

        enum_windows(enum_proc_type(callback), 0)

    def worker():
        while not stop_event.is_set():
            try:
                apply_icon()
            except Exception:
                pass
            stop_event.wait(0.15)

    thread = threading.Thread(target=worker, name="taskbar-icon", daemon=True)
    thread.start()

    def cleanup():
        stop_event.set()
        thread.join(timeout=1.0)
        handles = {large_handle, small_handle}
        for handle in handles:
            if handle:
                try:
                    destroy_icon(handle)
                except Exception:
                    pass

    return cleanup


def safe_cache_component(value):
    rendered = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return rendered or "python-app"


def logical_project_path(path, payload_dir, launcher_dir):
    absolute = os.path.abspath(path)
    try:
        relative = os.path.relpath(absolute, payload_dir)
    except ValueError:
        return absolute
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return absolute
    if relative == os.curdir:
        return launcher_dir
    return os.path.normpath(os.path.join(launcher_dir, relative))


class LauncherSourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname, path, payload_dir, launcher_dir):
        super().__init__(fullname, path)
        self.payload_dir = payload_dir
        self.launcher_dir = launcher_dir

    def logical_path(self, path):
        return logical_project_path(path, self.payload_dir, self.launcher_dir)

    def source_to_code(self, data, path, *, _optimize=-1):
        return super().source_to_code(
            data,
            self.logical_path(path),
            _optimize=_optimize,
        )

    def exec_module(self, module):
        logical_path = self.logical_path(self.path)
        if logical_path != self.path:
            module.__file__ = logical_path
            module.__cached__ = None
            if module.__spec__ is not None:
                module.__spec__.origin = logical_path
                module.__spec__.cached = None
            if hasattr(module, "__path__"):
                external = os.path.dirname(logical_path)
                if external not in module.__path__:
                    module.__path__.append(external)
        return super().exec_module(module)


def install_logical_project_paths(payload_dir, launcher_dir):
    def source_loader(fullname, path):
        return LauncherSourceLoader(
            fullname,
            path,
            payload_dir,
            launcher_dir,
        )

    hook = importlib.machinery.FileFinder.path_hook(
        (source_loader, importlib.machinery.SOURCE_SUFFIXES),
        (
            importlib.machinery.SourcelessFileLoader,
            importlib.machinery.BYTECODE_SUFFIXES,
        ),
        (
            importlib.machinery.ExtensionFileLoader,
            importlib.machinery.EXTENSION_SUFFIXES,
        ),
    )
    sys.path_hooks.insert(0, hook)
    sys.path_importer_cache.pop(payload_dir, None)


def run_entry(entry, logical_entry):
    with open(entry, "rb") as source:
        code = compile(source.read(), logical_entry, "exec")
    globals_dict = {
        "__name__": "__main__",
        "__file__": logical_entry,
        "__cached__": None,
        "__doc__": None,
        "__loader__": None,
        "__package__": None,
        "__spec__": None,
    }
    exec(code, globals_dict)


def extract_payload(archive_path, config):
    app_name = safe_cache_component(config.get("title") or "python-app")
    payload_hash = config["payload_hash"]
    cache_dir = None
    candidates = [
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("TEMP"),
        os.path.dirname(archive_path),
    ]
    for base in candidates:
        if not base:
            continue
        candidate = os.path.join(
            base,
            "SystemPythonLaunchers",
            app_name,
            payload_hash,
        )
        try:
            parent = os.path.dirname(candidate)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            cache_dir = candidate
            break
        except OSError:
            continue
    if cache_dir is None:
        raise RuntimeError("没有可写的程序解压目录。")
    marker = os.path.join(cache_dir, ".complete")
    if os.path.isfile(marker):
        return cache_dir

    temporary = cache_dir + ".{}.tmp".format(os.getpid())
    if os.path.isdir(temporary):
        shutil.rmtree(temporary)
    os.makedirs(temporary)

    try:
        prefix = "payload/"
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.infolist():
                if not member.filename.startswith(prefix):
                    continue
                relative = member.filename[len(prefix):]
                if not relative or relative.endswith("/"):
                    continue
                normalized = os.path.normpath(relative.replace("/", os.sep))
                if normalized == os.pardir or normalized.startswith(os.pardir + os.sep):
                    raise RuntimeError("程序包中存在不安全路径：{}".format(relative))
                target = os.path.join(temporary, normalized)
                parent = os.path.dirname(target)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent)
                with archive.open(member, "r") as source, open(target, "wb") as destination:
                    shutil.copyfileobj(source, destination)

        with open(os.path.join(temporary, ".complete"), "w", encoding="utf-8") as handle:
            handle.write(payload_hash)

        parent = os.path.dirname(cache_dir)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        try:
            os.replace(temporary, cache_dir)
        except OSError:
            if not os.path.isfile(marker):
                raise
            shutil.rmtree(temporary)
        return cache_dir
    except Exception:
        if os.path.isdir(temporary):
            shutil.rmtree(temporary)
        raise


def main():
    archive_path = os.path.abspath(sys.argv[0])
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            config = json.loads(archive.read(CONFIG_MEMBER).decode("utf-8"))
    except Exception as exc:
        show_error(
            "Python 启动器",
            "程序包损坏或配置无法读取。\n\n{}".format(exc),
            False,
        )
        return 2

    console = bool(config.get("console"))
    title = config.get("title") or "Python 程序"
    cleanup_taskbar_icon = install_taskbar_icon(archive_path, title)
    try:
        launcher_dir = os.path.dirname(archive_path)
        os.environ["SYSTEM_PYTHON_LAUNCHER_DIR"] = launcher_dir
        payload_dir = extract_payload(archive_path, config)
        source_only = bool(config.get("source_only"))
        entry_only = bool(config.get("entry_only"))
        sys._MEIPASS = launcher_dir if source_only else payload_dir
        entry = os.path.join(payload_dir, config["entry"].replace("/", os.sep))
        if not os.path.isfile(entry):
            raise RuntimeError("入口文件不存在：{}".format(entry))

        logical_entry = entry
        if source_only:
            logical_entry = logical_project_path(entry, payload_dir, launcher_dir)
            if not entry_only:
                install_logical_project_paths(payload_dir, launcher_dir)

        if payload_dir not in sys.path:
            sys.path.insert(0, payload_dir)
        if source_only and launcher_dir not in sys.path:
            sys.path.insert(1, launcher_dir)
        if entry_only:
            # Preserve sibling imports of an entry such as src/main.py.
            script_dir = os.path.dirname(logical_entry)
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
        sys.argv[0] = logical_entry
        if source_only:
            run_entry(entry, logical_entry)
        else:
            runpy.run_path(entry, run_name="__main__")
        return 0
    except SystemExit as exc:
        if exc.code is None:
            return 0
        if isinstance(exc.code, int):
            return exc.code
        show_error(title, str(exc.code), console)
        return 1
    except Exception:
        detail = traceback.format_exc()
        show_error(title, "程序运行失败：\n\n{}".format(detail[-5000:]), console)
        return 1
    finally:
        cleanup_taskbar_icon()


if __name__ == "__main__":
    raise SystemExit(main())
'''


def native_stub_bytes(console: bool) -> bytes:
    encoded = CONSOLE_STUB_B64 if console else GUI_STUB_B64
    return zlib.decompress(base64.b64decode(encoded))


def _resource_pointer(value: int) -> ctypes.c_void_p:
    return ctypes.c_void_p(value)


def update_executable_icon(executable: Path, icon: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("设置 EXE 图标仅支持 Windows。")
    data = icon.read_bytes()
    if len(data) < 6:
        raise ValueError("ICO 文件过短。")
    reserved, icon_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or icon_type != 1 or count < 1:
        raise ValueError("不是有效的 ICO 文件。")
    if len(data) < 6 + count * 16:
        raise ValueError("ICO 文件目录不完整。")

    entries: list[tuple[bytes, tuple[int, ...]]] = []
    group = bytearray(struct.pack("<HHH", 0, 1, count))
    for index in range(count):
        values = struct.unpack_from("<BBBBHHII", data, 6 + index * 16)
        width, height, colors, entry_reserved, planes, bits, size, offset = values
        end = offset + size
        if offset < 0 or size < 1 or end > len(data):
            raise ValueError("ICO 文件中的图像偏移无效。")
        resource_id = index + 1
        image = data[offset:end]
        entries.append((image, values))
        group.extend(
            struct.pack(
                "<BBBBHHIH",
                width,
                height,
                colors,
                entry_reserved,
                planes,
                bits,
                size,
                resource_id,
            )
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    begin = kernel32.BeginUpdateResourceW
    begin.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    begin.restype = wintypes.HANDLE
    update = kernel32.UpdateResourceW
    update.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.WORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    update.restype = wintypes.BOOL
    end_update = kernel32.EndUpdateResourceW
    end_update.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    end_update.restype = wintypes.BOOL

    handle = begin(str(executable), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    committed = False
    buffers: list[ctypes.Array] = []
    try:
        for resource_id, (image, _values) in enumerate(entries, start=1):
            buffer = ctypes.create_string_buffer(image)
            buffers.append(buffer)
            if not update(
                handle,
                _resource_pointer(3),
                _resource_pointer(resource_id),
                0,
                ctypes.cast(buffer, ctypes.c_void_p),
                len(image),
            ):
                raise ctypes.WinError(ctypes.get_last_error())

        group_buffer = ctypes.create_string_buffer(bytes(group))
        buffers.append(group_buffer)
        if not update(
            handle,
            _resource_pointer(14),
            _resource_pointer(1),
            0,
            ctypes.cast(group_buffer, ctypes.c_void_p),
            len(group),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        if not end_update(handle, False):
            raise ctypes.WinError(ctypes.get_last_error())
        committed = True
    finally:
        if not committed:
            end_update(handle, True)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def collect_project_files(
    project: Path,
    output_directory: Path | None = None,
    source_only: bool = False,
) -> list[tuple[Path, Path]]:
    project = project.resolve()
    excluded_output = output_directory.resolve() if output_directory else None
    if excluded_output == project:
        excluded_output = None
    files: list[tuple[Path, Path]] = []
    visited: set[Path] = set()
    for root, directories, filenames in os.walk(project):
        root_path = Path(root)
        resolved_root = root_path.resolve()
        if resolved_root in visited or not _is_within(resolved_root, project):
            directories[:] = []
            continue
        visited.add(resolved_root)
        kept_directories: list[str] = []
        for directory in sorted(directories, key=str.casefold):
            candidate = root_path / directory
            if directory in DEFAULT_SKIP_DIRS or candidate.is_symlink():
                continue
            if not _is_within(candidate.resolve(), project) or candidate.resolve() in visited:
                continue
            if excluded_output is not None and _is_within(candidate.resolve(), excluded_output):
                continue
            kept_directories.append(directory)
        directories[:] = kept_directories

        for filename in sorted(filenames, key=str.casefold):
            path = root_path / filename
            if path.is_symlink():
                continue
            if not _is_within(path.resolve(), project):
                continue
            if source_only:
                if path.suffix.casefold() not in {".py", ".pyw"}:
                    continue
            else:
                if filename.casefold() == PROJECT_SETTINGS_FILENAME.casefold():
                    continue
                if path.suffix.casefold() in {".pyc", ".pyo"}:
                    continue
            if excluded_output is not None and _is_within(path.resolve(), excluded_output):
                continue
            files.append((path, path.relative_to(project)))
    return files


def _payload_digest(
    files: list[tuple[Path, Path]],
    cancelled: Callable[[], bool] | None = None,
) -> str:
    digest = hashlib.sha256()
    for source, relative in files:
        if cancelled and cancelled():
            raise InterruptedError("任务已取消")
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with source.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                if cancelled and cancelled():
                    raise InterruptedError("任务已取消")
        digest.update(b"\0")
    return digest.hexdigest()


def build_system_python_launcher(
    *,
    project: Path,
    entry: Path,
    output: Path,
    title: str,
    console: bool,
    source_only: bool = False,
    entry_only: bool = False,
    icon_path: Path | None = None,
    log: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, object]:
    project = project.resolve()
    entry = entry.resolve()
    output = output.resolve()
    try:
        entry_relative = entry.relative_to(project)
    except ValueError as exc:
        raise ValueError("系统 Python 启动器要求入口文件位于项目目录内。") from exc

    source_only = source_only or entry_only
    if entry_only:
        if not entry.is_file() or entry.suffix.casefold() not in {".py", ".pyw"}:
            raise ValueError("入口包装需要有效的 .py 或 .pyw 入口文件。")
        files = [(entry, entry_relative)]
        excluded_existing_executables = []
    else:
        collected_files = collect_project_files(
            project,
            output.parent,
            source_only=source_only,
        )
        excluded_existing_executables = [
            relative
            for source, relative in collected_files
            if source.suffix.casefold() == ".exe"
            and source.name.casefold() == output.name.casefold()
        ]
        files = [
            item
            for item in collected_files
            if item[0].resolve() != output
            and not (
                item[0].suffix.casefold() == ".exe"
                and item[0].name.casefold() == output.name.casefold()
            )
        ]
        if not any(relative == entry_relative for _source, relative in files):
            raise ValueError("入口文件被排除或无法加入程序包。")
    if cancelled and cancelled():
        raise InterruptedError("任务已取消")

    if log:
        if entry_only:
            log(f"入口包装：{entry_relative.as_posix()}")
            log("同项目的其他模块和资源由 EXE 所在目录提供")
        elif source_only:
            log("收集 Python 源码：{} 个".format(len(files)))
            log("仅输出 EXE，外部资源由项目自行管理")
        else:
            log("收集完整项目文件：{} 个".format(len(files)))
            log("资源文件：内置到 EXE")
        log("依赖检查：关闭，由系统 Python 在运行时处理")
        if excluded_existing_executables:
            log(
                "已排除同名历史 EXE：{}".format(
                    "、".join(
                        path.as_posix()
                        for path in excluded_existing_executables[:10]
                    )
                )
            )

    payload_hash = _payload_digest(files, cancelled)
    config = {
        "format": 1,
        "title": title,
        "entry": entry_relative.as_posix(),
        "console": console,
        "source_only": source_only,
        "payload_hash": payload_hash,
    }

    if entry_only:
        config["entry_only"] = True

    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage on the destination volume so replacement is atomic across drives.
    with tempfile.TemporaryDirectory(prefix=".launcher-stage-", dir=output.parent) as staging:
        temporary_output = Path(staging) / "launcher.exe"
        temporary_output.write_bytes(native_stub_bytes(console))
        if icon_path is not None:
            update_executable_icon(temporary_output, icon_path)

        with zipfile.ZipFile(
            temporary_output,
            mode="a",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
        ) as archive:
            archive.writestr("__main__.py", BOOTSTRAP_SOURCE.encode("utf-8"))
            archive.writestr(
                "__launcher__/config.json",
                json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            for index, (source, relative) in enumerate(files, start=1):
                if cancelled and cancelled():
                    raise InterruptedError("任务已取消")
                archive.write(source, "payload/" + relative.as_posix())
                if log and (index == len(files) or index % 100 == 0):
                    label = "Python 源码" if source_only else "项目文件"
                    log("正在写入{}：{}/{}".format(label, index, len(files)))

        if not is_system_python_launcher(temporary_output):
            raise RuntimeError("输出校验失败：生成结果不是系统 Python 启动器。")
        if cancelled and cancelled():
            raise InterruptedError("任务已取消")
        os.replace(temporary_output, output)

    return {
        "output": output,
        "file_count": len(files),
        "external_file_count": 0,
        "payload_hash": payload_hash,
        "source_only": source_only,
        "excluded_existing_executables": excluded_existing_executables,
    }


def is_system_python_launcher(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            if "__main__.py" not in names or "__launcher__/config.json" not in names:
                return False
            config = json.loads(
                archive.read("__launcher__/config.json").decode("utf-8")
            )
    except (OSError, ValueError, KeyError, UnicodeError, zipfile.BadZipFile):
        return False
    return config.get("format") == 1 and bool(config.get("entry"))
