import heterocl as hcl
import numpy as np
import tvm

cordic_ctab = [0.78539816339744828000,0.46364760900080609000,0.24497866312686414000,0.12435499454676144000,0.06241880999595735000,0.03123983343026827700,0.01562372862047683100,0.00781234106010111110,0.00390623013196697180,0.00195312251647881880,0.00097656218955931946,0.00048828121119489829,0.00024414062014936177,0.00012207031189367021,0.00006103515617420877,0.00003051757811552610,0.00001525878906131576,0.00000762939453110197,0.00000381469726560650,0.00000190734863281019,0.00000095367431640596,0.00000047683715820309,0.00000023841857910156,0.00000011920928955078,0.00000005960464477539,0.00000002980232238770,0.00000001490116119385,0.00000000745058059692,0.00000000372529029846,0.00000000186264514923,0.00000000093132257462,0.00000000046566128731,0.00000000023283064365,0.00000000011641532183,0.00000000005820766091,0.00000000002910383046,0.00000000001455191523,0.00000000000727595761,0.00000000000363797881,0.00000000000181898940,0.00000000000090949470,0.00000000000045474735,0.00000000000022737368,0.00000000000011368684,0.00000000000005684342,0.00000000000002842171,0.00000000000001421085,0.00000000000000710543,0.00000000000000355271,0.00000000000000177636,0.00000000000000088818,0.00000000000000044409,0.00000000000000022204,0.00000000000000011102,0.00000000000000005551,0.00000000000000002776,0.00000000000000001388,0.00000000000000000694,0.00000000000000000347,0.00000000000000000173,0.00000000000000000087,0.00000000000000000043,0.00000000000000000022,0.00000000000000000011]

K_const = 0.6072529350088812561694

def top(dtype):

  def step_loop(X, Y, T, C, theta, current, step):
    with hcl.CodeBuilder() as cb:
      with cb._if(theta[0] > current[0]):
        T[0] = X[0] - (Y[0] >> step)
        Y[0] = Y[0] + (X[0] >> step)
        X[0] = T[0]
        current[0] = current[0] + C[step]
      with cb._else():
        T[0] = X[0] + (Y[0] >> step)
        Y[0] = Y[0] - (X[0] >> step)
        X[0] = T[0]
        current[0] = current[0] - C[step]

  X = hcl.placeholder((1,), name = "X")
  Y = hcl.placeholder((1,), name = "Y")
  T = hcl.compute((1,), [], lambda x: 0, name = "T")
  C = hcl.placeholder((64,), name = "cordic_ctab")
  theta = hcl.placeholder((1,), name = "theta")
  current = hcl.compute((1,), [], lambda x: 0, name = "current")
  N = hcl.var(name = "N")

  calc = hcl.mut_compute((N,), [X, Y, T, C, theta, current], lambda x: step_loop(X, Y, T, C, theta, current, x))

  hcl.resize([X, Y, T, C, theta, current], dtype)

  s = hcl.create_schedule(calc)

  #print tvm.lower(s, [X.tensor, Y.tensor, T.tensor, C.tensor, theta.tensor, current.tensor, N.var], simple_mode = True)
  return hcl.build(s, [X, Y, C, theta, N])

import math


NUM = 90
N = 60

for b in xrange(2, 64, 4):

  dtype = hcl.Fixed(b, b-2)
  f = top(dtype)

  acc_err_sin = 0.0
  acc_err_cos = 0.0

  for d in range(1, NUM):

    _d = math.radians(d)
    ms = math.sin(_d)
    mc = math.cos(_d)

    _X = hcl.asarray(np.array([K_const]), dtype = dtype)
    _Y = hcl.asarray(np.array([0]), dtype = dtype)
    _T = hcl.asarray(np.array([0]), dtype = dtype)
    _C = hcl.asarray(np.array(cordic_ctab), dtype = dtype)
    _theta = hcl.asarray(np.array([_d]), dtype = dtype)
    _current = hcl.asarray(np.array([0]), dtype = dtype)

    f(_X, _Y, _C, _theta, N)

    _X = _X.asnumpy()
    _Y = _Y.asnumpy()

    err_ratio_sin = math.fabs((ms - _Y[0])/ms) * 100
    err_ratio_cos = math.fabs((mc - _X[0])/mc) * 100

    acc_err_sin += err_ratio_sin * err_ratio_sin
    acc_err_cos += err_ratio_cos * err_ratio_cos

  print str(dtype) + ": " + str(math.sqrt(acc_err_sin/(NUM-1))) + " " + str(math.sqrt(acc_err_cos/(NUM-1)))

