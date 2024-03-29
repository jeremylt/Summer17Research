def element_setup():
    # Inputs:
    #       p_deg - degree of shape functions
    #       q_deg - degree of quadrature

    # Outputs:
    #       B - mass matrix component
    #       D - stiffness matrix component
    #       q - quadrature points
    #       W - quadrature weights

    # Quadrature Points and Weights
    q, w = np.polynomial.legendre.leggauss(q_deg)
    W = np.diag(w)

    # B, D matrices
    nodes = np.linspace(-1, 1, p_deg + 1)
    poly = np.polynomial.legendre.Legendre.basis(p_deg, [-1, 1]).deriv(1)
    nodes[1 : -1] = poly.roots()

    # B
    B = np.array(
        [np.prod([(q - nodes[j])/(nodes[i] - nodes[j]) for j in range(p_deg + 1) if j != i], 0)
         for i in range(p_deg + 1)])

    # D
    if p_deg == 1:
        D = np.array(
            [np.prod([(q - nodes[j]) / (nodes[i] - nodes[j]) for j in range(p_deg + 1) if j != i], 0)
             *np.sum([1/(q - nodes[j]) for j in range(p_deg + 1) if j != i], 0)
             for i in range(p_deg + 1)])
        # Smaller expression, but does not allow for odd deg of quadrature
    else:
        D = np.array(
            [np.sum([np.prod([(q - nodes[j]) / (nodes[i] - nodes[j]) for j in range(p_deg + 1) if j != i and j != k], 0)
                      / (nodes[i] - nodes[k])
             for k in range(p_deg + 1) if k != i], 0)
             for i in range(p_deg + 1)])

    return B.T, D.T, q, W

def apply_M(u):
    # Inputs:
    #       u - input vector
    #       B - mass matrix component
    #       q - quadrature points
    #       W - quadrature weights
    #       J - Jacobian

    # Outputs:
    #       Mu - Mu = Sum E'B'W|J|BEu

    # Setup
    Mu = np.zeros(pts)

    for i in range(n):
        # Add to Mu
        Mu[i * p_deg: (i + 1) * p_deg + 1] += np.dot(B.T, J * W.dot(B.dot(u[i * p_deg: (i + 1) * p_deg + 1])))

    return Mu

def apply_L(u):
    # Inputs:
    #       u - input vector
    #       D - stiffness matrix component
    #       q - quadrature points
    #       W - quadrature weights
    #       J - Jacobian
    #       dX - change of coordinates

    # Outputs:
    #       Lu - Lu = Sum E'D'(dX/dx)'W|J|(dX/dx)DEu

    # Setup
    Lu = np.zeros(pts)

    for i in range(n):
        # Add to Lu
        Lu[i * p_deg: (i + 1) * p_deg + 1] += np.dot(D.T, dX * W.dot(J * dX * D.dot(u[i * p_deg: (i + 1) * p_deg + 1])))

    return Lu

def apply_LHS(u):
    # Apply Operators
    u_return = -apply_L(u)

    return u_return

def apply_bc(u):
    # Setup Boundaries
    u_return = u_boundary.copy()

    # Apply Operators
    u_return[1 : -1] = u[1 : -1]

    return u_return

def apply_zero_bc(u):
    # Setup Boundaries
    u_return = np.zeros(pts)

    # Apply Operators
    u_return[1 : -1] = u[1 : -1]

    return u_return

def get_bc(u):
    # Setup Boundaries
    u_return = np.zeros(pts)

    # Apply Operators
    u_return[0] = u[0]
    u_return[-1] = u[-1]

    return u_return


# Main Code
# Setup
import numpy as np
import matplotlib.pyplot as plt

p_degs = range(1, 6)
run_errs = np.zeros((max(p_degs) + 1, 10))
run_delx = run_errs.copy()

q_deg = 8                           # degree of quadrature

def f(x):       # forcing function
    #return (18 * np.pi**2 - 36 * np.pi * x + 12 * x**2) / 500
    from numpy import tanh, sin, cos
    return (2*(tanh(x)**2 - 1)*sin(x)*tanh(x) - 2*(tanh(x)**2 - 1)*cos(x) - sin(x)*tanh(x))

def f_true(x):  # true function
    #return (x**2 * (x - 3 * np.pi)**2) / 500
    return np.tanh(x)*np.sin(x) + x

# Run FE with different p_deg, n
for p_deg in p_degs:
    print(p_deg)
    for n in range(10, 70, 10):
        # Setup
        pts = n * (p_deg + 1) - (n - 1)     # number of points

        I = [0, 3 * np.pi]                  # interval
        h = (I[1] - I[0]) / n               # element width

        u_boundary = np.zeros(pts)  # boundary
        u_boundary[0] = 0
        u_boundary[-1] = I[1]

        # Setup Element
        B, D, q, W = element_setup()

        # Build J, (dX/dx)
        # 1D uniform grid
        # x = (X + 1) * h / 2 + a
        # dx/dX = h / 2
        # |J| = h / 2
        dX = 2 / h
        J = h / 2

        # Build Load Vector
        Mf = np.zeros(pts)

        for i in range(n):
            Mf[i * p_deg: (i + 1) * p_deg + 1] += np.dot(B.T, J * W.dot(f((q + 1) / dX + h * i)))

        # Iterate to solution
        # Conjugate gradient
        u_old = np.random.rand(pts)
        u_old = apply_bc(u_old)
        r_temp = Mf - apply_LHS(apply_bc(u_old))
        r_old = apply_zero_bc(r_temp) + (get_bc(u_old) - u_boundary)
        p_old = r_old.copy()
        r_new = r_old.copy()
        norm = 1
        itr = 1

        while norm > 10 ** -16 and itr < 20 * pts:
            # Calculate new values
            a = np.dot(r_old.T, r_old) / np.dot(p_old.T, apply_LHS(p_old))
            u_new = u_old + a * p_old
            r_temp = Mf - apply_LHS(apply_bc(u_new))
            r_new = apply_zero_bc(r_temp) + (get_bc(u_old) - u_boundary)
            b = np.dot(r_new.T, r_new) / np.dot(r_old.T, r_old)
            p_new = r_new + b * p_old

            # Calculate error
            norm = np.max(np.abs(r_new))

            # Prepare for next iteration
            itr += 1
            u_old = u_new.copy()
            r_old = r_new.copy()
            p_old = p_new.copy()

        # Calculate error
        x_vals = np.linspace(I[0], I[1], pts)
        poly = np.polynomial.legendre.Legendre.basis(p_deg, [-1, 1]).deriv(1)
        for i in range(n):
            x_vals[i * p_deg + 1: (i + 1) * p_deg] = (poly.roots() + 1) * J + h * i

        u_true = f_true(x_vals)
        norm = np.max(np.abs(u_true - u_new))

        run_errs[p_deg, int(n / 10)] = norm
        run_delx[p_deg, int(n / 10)] = h / p_deg

# Plot
symbols = iter(['o', '^', 's', '*', '>', '+'])
for p_deg in p_degs:
    plt.loglog(run_delx[p_deg, :], run_errs[p_deg, :], next(symbols), label = 'p = '+str(p_deg))
    plt.loglog(run_delx[p_deg, :], run_delx[p_deg, :]**(p_deg+1), label='$h^{%d}$'%(p_deg+1))
plt.legend()
plt.xlabel('dx')
plt.ylabel('||error||')
plt.title('Error vs dx')
plt.show()

# Plot last result
plt.plot(x_vals, u_true, label = 'True Solution')
plt.plot(x_vals, u_new, label = 'Calculated Solution')
plt.legend()
plt.xlabel('x')
plt.ylabel('u')
plt.title('Calculated vs True')
plt.axis([I[0], I[1], 1.05 * np.min(u_true), 1.05 * np.max(u_true)])
plt.show()
