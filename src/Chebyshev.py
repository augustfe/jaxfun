from functools import partial
from common import diff
import jax 
from jax import Array 
import jax.numpy as jnp
import sympy as sp 

s = sp.Symbol('s')

@jax.jit
def chebval(x : float, c : Array) -> float:
    """
    Evaluate a Chebyshev series at points x.

    .. math:: p(x) = c_0 * T_0(x) + c_1 * T_1(x) + ... + c_n * T_n(x)

    Parameters
    ----------
    x : float
    c : Array
        
    Returns
    -------
    values : Array
    
    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    """
    #return jnp.sum(jax.vmap(lambda k: c[k]*jnp.cos(k*jnp.acos(x)))(jnp.arange(len(c))), axis=0)
    if len(c) == 1:
        c0 = c[0]
        c1 = 0
    elif len(c) == 2:
        c0 = c[0]
        c1 = c[1]
    else:
        x2 = 2*x
        c0 = c[-2]
        c1 = c[-1]
        for i in range(3, len(c) + 1):
            tmp = c0
            c0 = c[-i] - c1
            c1 = tmp + c1*x2
    return c0 + c1*x

def quad_points_and_weights(N : int) -> Array:
    return jnp.array((jnp.cos(jnp.pi+(2*jnp.arange(N)+1)*jnp.pi/(2*N)),
                      jnp.ones(N)*jnp.pi/N))

@partial(jax.jit, static_argnums=(1, 2))
def evaluate_basis_derivative(x : Array, deg : int, k : int = 0) -> Array:
    c = jnp.eye(deg)
    f = jax.vmap(lambda i: diff(chebval, k=k)(x, c[i]))(jnp.arange(deg))
    return jnp.moveaxis(f, 0, -1)

@partial(jax.jit, static_argnums=1)
def eval_basis_function(x : float, i : int) -> float:
    return jnp.cos(i*jnp.acos(x))
    #return chebval(x, (0,)*i+(1,))

@partial(jax.jit, static_argnums=2)
def evaluate(x : Array, c : Array, axes : tuple[int] = (0,)) -> Array:
    """Evaluate along one or more axes"""
    dim : int = len(c.shape)
    for ax in axes:
        axi : int = dim-1-ax
        c = jax.vmap(chebval, in_axes=(None, axi))(x, c)
    return c

@partial(jax.jit, static_argnums=1)
def chebvander(x : Array, deg : int) -> Array:
    f = [x*0 + 1]
    if deg > 0:
        x2 = 2*x
        f.append(x)
        for i in range(2, deg):
            f.append(f[i-1]*x2 - f[i-2])
    f = jnp.array(f)
    return jnp.moveaxis(f, 0, -1)

def bilinear(N : int, i : int, j : int) -> Array:
    x, w = quad_points_and_weights(N)
    Pi = evaluate_basis_derivative(x, N, k=i)
    Pj = evaluate_basis_derivative(x, N, k=j)
    return (Pi.T * w[None, :]) @ Pj 

def linear(u, N : int) -> Array:
    x, w = quad_points_and_weights(N)
    Pi = chebvander(x, N)
    uj = sp.lambdify(s, u, modules=['jax'])(x)
    return (uj * w) @ Pi 

if __name__ == '__main__':
    # Solve Poisson's equation 
    import matplotlib.pyplot as plt
    from jax.experimental import sparse
    ue = (1-s**2)*sp.exp(sp.cos(2*sp.pi*s))
    f = ue.diff(s, 2)
    N = 50
    S = sparse.eye(N, N+2) - sparse.eye(N, N+2, 2) # Dirichlet
    A = S @ bilinear(N+2, 0, 2) @ S.T
    b = S @ linear(f, N+2)
    u = jnp.linalg.solve(A, b)
    x = jnp.linspace(-1, 1, 100)
    plt.plot(x, sp.lambdify(s, ue)(x), 'r')
    plt.plot(x, chebval(x, u @ S), 'b')
    plt.show()