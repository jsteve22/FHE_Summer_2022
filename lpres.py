#!/usr/bin/env python
# this program will be an attempt to create the lpr.es
# encrption scheme that is described in the BFV paper.
# This encryption scheme will then be transformed into 
# a SWHE which will then be turned into a FHE scheme
#
#
# this will also have some testing code for me to test
# polynomial ring operations

import numpy as np
from numpy.polynomial import polynomial as p
import sys
from poly import Poly

def main():
	# this main function is using the lpr() class
	# encryption scheme

	test_addition()
	print('\n')
	test_multiplication()
	print('\n')
	#lpr_test()
	#ring_test()
	
	n = 2**4
	q = 2**15
	t = 2**8
	lpr = LPR(q=q,t=t,n=n)

	#lpr.sk.polyprint()
	#lpr.pk[0].polyprint()
	#lpr.pk[1].polyprint()
	#print( lpr.pk )

	pt = 5
	#pt = np.random.randint(0,50)

	ct = lpr.encrypt(pt)


	#ct[0].polyprint()
	#ct[1].polyprint()

	recovered_pt = lpr.decrypt(ct)

	print(f'original pt: {pt}\trecovered pt: {recovered_pt}')
	print(f'{pt==recovered_pt}')

	return

class LPR():

	def __init__(self,q=2**15,t=2**8,n=2**4,fn=None,T=None):
		# this init method will initialize the important variables
		# needed for this encryption scheme
		self.q = q
		self.t = t
		self.n = n
		# this will set the polynomial for the ring, if not declared then will be
		# the polynomial 1 + x^n
		self.fn = fn
		if (self.fn == None):
			self.fn = [1] + [0]*(n-1) + [1]
		self.fn = Poly(self.fn)
		# this will set the variable T, as needed for relinearization1 for BFV
		self.T = T
		if (self.T == None):
			# if not defined, set T as the square root of q, rounded to highest up
			self.T = int(np.ceil(np.sqrt(self.q)))

		# this will set the keys as none, but will then immediately generate
		# a public key, a private key, and a relinearization key
		self.sk = None
		self.pk = None
		self.rlk = None
		self.gen_keys()

	def gen_keys(self):
		# calls the different functions to generate the keys
		self.gensk()
		self.genpk()
		self.genrlk1()
		
	def gensk(self):
		# call the gen_binary_poly key to create a polynomial
		# of only 0's and 1's for the secret key
		self.sk = self.gen_binary_poly()
		#self.sk = self.gen_normal_poly()
		return

	def genpk(self):
		if (self.sk == None):
			return
		# generate a uniformly distributed polynomial with coefs
		# from [0,q)
		a = self.gen_uniform_poly()

		# create a new polynomial _a which is -a
		_a = []
		for i in a:
			_a.append(-1*i)
		_a = Poly(_a)

		# generate a normally distributed polynomial with integers
		# generated from a center of 0 and std of 2
		e = self.gen_normal_poly()
		# then set e = -e
		for ind, i in enumerate(e):
			e[ind] = -1 * i

		# create b from (-a * sk) - e
		b = self.polyadd( self.polymult(_a, self.sk),e)

		# set the public key to the tuple (b,a)
		# or (-[a*sk + e], a)
		self.pk = (b,a)
		return
	
	def genrlk1(self):
		# use change of base rule for logs to calculate logT(q)
		# using log2 because most likely self.q and self.T are in base 2
		self.l = int(np.floor(np.log2(self.q)/np.log2(self.T)))

		# create the different masks for the rlk key
		self.rlk = []
		ss = self.polymult(self.sk,self.sk)
		#a = self.gen_uniform_poly()
		#e = self.gen_normal_poly()
		for i in range(self.l+1):
			# generate the different random polynomials needed
			a = self.gen_uniform_poly()
			e = self.gen_normal_poly()
			_a = a.copy()
			for jnd, j in enumerate(_a):
				_a[jnd] = -1 * j
			for jnd, j in enumerate(e):
				e[jnd] = -1 * j

			b = self.polyadd( self.polymult(_a, self.sk), e)
			'''
			b = self.polyadd( self.polymult(a, self.sk), e)
			for jnd, j in enumerate(b):
				b[jnd] = -1 * j
				'''
			T = self.T ** i
			'''
			print(f'T = {T}')
			print('sk:',end=' ')
			self.sk.polyprint()
			print("sk^2:",end=' ')
			ss.polyprint()
			'''
			s2 = ss.copy()
			for jnd, j in enumerate(s2):
				s2[jnd] = j * T 
			#print("T*sk^2:",end=' ')
			#s2.polyprint()
			b = self.polyadd( b, s2 )
			self.rlk.append( (b,a) )
			
		#self.rlk = rlk.copy()
		return
	
	
	def encrypt(self,pt=0):
		# encode plaintext into a plaintext polynomial
		# create polynomial m, which is pt%q
		m = [pt]
		m = Poly(m)
		m = m % self.q

		delta = self.q // self.t
		scaled_m = m.copy()
		scaled_m[0] = delta * scaled_m[0] % self.q
		# create a new m, which is scaled my q//t % q
		# generated new error polynomials
		e1 = self.gen_normal_poly()
		e2 = self.gen_normal_poly()
		u = self.gen_binary_poly()
		# create c0 = pk[0]*u + e1 + scaled_m
		ct0 = self.polyadd( self.polyadd( self.polymult( self.pk[0], u), e1), scaled_m)

		# create c1 = pk[1]*u + e2
		ct1 = self.polyadd( self.polymult( self.pk[1], u), e2)

		return (ct0, ct1)

	def decrypt(self,ct):
		# decrypt the cipher text to get the plaintext equivalent

		# scaled_pt = ct[1]*sk + ct[0]
		scaled_pt = self.polyadd( self.polymult( ct[1], self.sk ), ct[0] )
		decrypted_pt = []
		# scale each coefficient by t/q % t
		for ind, i in enumerate( scaled_pt ):
			decrypted_pt.append(  round(i * self.t / self.q ) % self.t )
		
		# create a polynomial from the list
		decrypted_pt = Poly(decrypted_pt)

		# return the first term of the polynomial, which is the plaintext
		return int(decrypted_pt[0])

	def ctadd(self, x, y):
		# X and Y are two cipher texts generated
		# by this encrypted scheme
		ct0 = self.polyadd(x[0],y[0])
		ct1 = self.polyadd(x[1],y[1])

		ct = (ct0,ct1)

		return ct

	def ctmult(self, x, y, type=1):
		# multiply cipher texts X and Y and return ciphertext X*Y
		# still work in progress, not working yet

		# calculate c0 
		c0 = self.polymult( x[0], y[0] )
		for ind, i in enumerate(c0):
			c0[ind] = round(i * self.t / self.q) #% self.q
		
		c0 = self.mod(c0)

		# calculate c1
		t0 = self.polymult(x[1],y[0])
		t1 = self.polymult(x[0],y[1])
		c1 = self.polyadd( t0, t1)
		for ind, i in enumerate(c1):
			c1[ind] = round(i * self.t / self.q) #% self.q
		
		c1 = self.mod(c1)

		# calculate c2
		c2 = self.polymult( x[1], y[1] )
		for ind, i in enumerate(c2):
			c2[ind] = round(i * self.t / self.q) #% self.q

		c2 = self.mod(c2)

		ret = self.relin1(c0,c1,c2)

		return ret
		# relinearization without new base T

		a = self.gen_normal_poly()
		e = self.gen_binary_poly()

		ask = self.polymult( a, self.sk )
		b = self.polyadd( ask, e )
		for ind, i in enumerate(b):
			b[ind] = -1 * i
		
		ss = self.polymult(self.sk, self.sk)
		ek = ( self.polyadd(b,ss), a )

		r0 = self.polyadd( c0, self.polymult(ek[0],c2 ) )
		r1 = self.polyadd( c1, self.polymult(ek[1],c2 ) )
	
		#ret = (r0, r1)
		return ret

	def relin1(self,c0,c1,c2):
		# still work in progress, not completed
		# calculate c2T, which would be c2 in base T

		c2T = self.poly_base_change(c2,self.q,self.T)

		summ0 = Poly()
		summ1 = Poly()

		for i in range(self.l+1):
			summ0 = self.polyadd( summ0, self.polymult(self.rlk[i][0], c2T[i] ) )
			summ1 = self.polyadd( summ1, self.polymult(self.rlk[i][1], c2T[i] ) )
		
		_c0 = self.polyadd( c0, summ0 )
		_c1 = self.polyadd( c1, summ1 )

		return (_c0, _c1)

	def mod(self,poly):
		# calculate the modulus of poly by q
		# with answer given back in range (-q/2,q/2]
		copy = poly.poly.copy()
		for ind,i in enumerate(copy):
			i = i % self.q
			if ( i > (self.q/2) ):
				copy[ind] = i - self.q

		return Poly(copy)

	def polyadd(self, x, y):
		# add two polynomials together and keep them 
		# within the polynomial ring
		z = x + y
		quo,rem = (z / self.fn)
		z = rem
		for ind, i in enumerate(z):
			z[ind] = round(i)
		z = z % self.q
		z = self.mod(z)
		return z

	def polymult(self, x, y):
		# multiply two polynomials together and keep them 
		# within the polynomial ring
		z = x * y
		quo, rem = (z / self.fn)
		z = rem
		for ind, i in enumerate(z):
			z[ind] = round(i)
		z = z % self.q
		z = self.mod(z)
		return z

	def gen_normal_poly(self,c=0,std=2):
		# generate a random polynomial of degree n-1
		# with coefficients selected from normal distribution
		# with center at 0 and std of 2. Each term is rounded
		# down to nearest integer
		a = []
		for i in range(self.n):
			a.append( int(np.random.normal(c,std)) )
		a = Poly(a)
		return a

	def gen_binary_poly(self):
		# generate a random polynomial of degree n-1
		# with coefficients ranging from [0,1]
		a = []
		for i in range(self.n):
			a.append( np.random.randint(0,2) )
		a = Poly(a)
		return a

	def gen_uniform_poly(self,q=None):
		# generate a random polynomial of degree n-1
		# with coefficients ranging from [0,q)
		if (q == None):
			q = self.q
		a = []
		for i in range(self.n):
			a.append( np.random.randint(0,q) )
		a = Poly(a)

		return a

	def poly_base_change(self,poly,q,T):
		# change the base of a polynomial and
		# return multiple polynomials of new base
		# haven't tested this, don't know if it works
		l = int(np.floor(np.log2(q)/np.log2(T)))
		cpy = poly.copy()
		base_poly = []

		for ind, i in enumerate(cpy):
			if i < 0:
				cpy[ind] = i + self.q

		for i in range(l+1):
			mask = []
			for jnd, j in enumerate(cpy):
				_Tpow = T ** (i+1)
				_T = T ** i
				num = j % _Tpow
				mask.append( int( num / _T ) )
				cpy[jnd] -= num

			base_poly.append( Poly(mask) )

		return base_poly


def ring_test():

	A = [4,1,11,10]
	sA = [6,9,11,11]
	eA = [0,-1,1,1]
	n=4
	q=13

	xN_1 = [1] + [0]*(n-1) + [1]

	A = np.floor(p.polydiv(A,xN_1)[1])
	bA = p.polymul(A,sA)%q
	bA = np.floor(p.polydiv(bA,xN_1)[1])
	bA = p.polyadd(bA,eA)%q
	bA = np.floor(p.polydiv(bA,xN_1)[1])

	print(bA)
	return

def lpr_test():
	q = 2**15
	n = 2**4
	fn = [1] + [0]*(n-1) + [1]
	t = 2**8
	delta = int(q/t)

	'''
	print('q: ',q)
	print('t: ',t)
	print('delta: ',delta)
	'''

	#sk = skgen(n,q)
	sk = [1,0,0]

	pk = pkgen(sk,n,q,fn)


	#print(sk)
	#print(pk)
	#print(len(pk[0]))

	# message to encrypt/decrypt
	m = [1] + [0]*(n-1)
	m = np.array(m)

	ct = encrypt(m,pk,n,q,fn,delta)

	#print(ct)

	pt = decrypt(ct,sk,n,q,t,fn)

	print(pt)

	return

def skgen(n,q):
	ret = np.random.randint(low=-2,high=3,size=[1,n])
	return ret[0]

def pkgen(s,n,q,fn):
	a = np.random.randint(low=0,high=q,size=[1,n])
	#e = np.random.randint(low=-2,high=3,size=[1,n])
	e = [[-1,1,0]]
	
	# create first argument of public key
	p0 = p.polymul(a[0],s)
	for ind,i in enumerate(p0):
		p0[ind] = mod(i,q)
	
	p0 = p.polyadd(p0,e[0])
	for ind,i in enumerate(p0):
		p0[ind] = mod(i,q)
	
	p0 = np.floor(p.polydiv(p0,fn)[1])
	p0 = p0 * -1

	# create second argument of public key
	p1 = a[0]

	return (p0,p1)

def encrypt(m,pk,n,q,fn,delta):
	u = np.random.randint(low=-1,high=2,size=[1,n])
	e1 = np.random.randint(low=-2,high=3,size=[1,n])
	e2 = np.random.randint(low=-2,high=3,size=[1,n])

	ct0 = p.polymul(pk[0],u[0])
	ct0 = np.floor(p.polydiv(ct0,fn)[1])
	ct0 = ct0 + e1[0]
	ct0 = ct0 + (delta*m)
	for ind,i in enumerate(ct0):
		ct0[ind] = mod(i,q)

	ct1 = p.polymul(pk[1],u[0])
	ct1 = np.floor(p.polydiv(ct1,fn)[1])
	ct1 = ct1 + e2[0]
	for ind,i in enumerate(ct1):
		ct1[ind] = mod(i,q)
	
	return (ct0,ct1)

def decrypt(ct,sk,n,q,t,fn):
	pt = p.polymul(ct[1],sk)
	pt = np.floor(p.polydiv(pt,fn)[1])
	pt = pt + ct[0]
	#pt = pt * t
	#pt = pt / q
	#pt = pt + 0.5
	for ind,i in enumerate(pt):
		i = i * t
		i = i * q
		i = i + 0.5
		pt[ind] = int(i)
		pt[ind] = mod(pt[ind],t)

	return pt

def mod(x,q=2):
	ret = x % q
	if (ret > (q/2)):
		ret = ret - q
	return ret

def test_addition():
	# this function will act as the test of adding two cipher texts

	lpr = LPR(t=2 ** 5)

	# generate the two random numbers
	#x = 1
	#y = 2
	x = np.random.randint(0,10)
	y = np.random.randint(0,10)
	print(f'{x} and {y} are randomly generated')

	ctx = lpr.encrypt(x)
	cty = lpr.encrypt(y)

	ctz = lpr.ctadd(ctx,cty)

	answer = lpr.decrypt(ctz)

	print(f'cipher text addition')
	print(f'{x} + {y} = {answer}')
	print(f'Addition test: { answer == (x+y) }')
	if (answer == (x+y) ):
		return 1
	else:
		return 0
	return

def test_multiplication():
	# this function will act as the test of adding two cipher texts

	#lpr = LPR(q=2**14,t=2**5,T=5)
	#lpr = LPR(n=2**7,t=2**4,q=2**20)
	lpr = LPR()

	# generate the two random numbers
	x = 0
	y = 0
	#x = np.random.randint(1,3)
	#y = np.random.randint(1,3)
	print(f'{x} and {y} are randomly generated')

	ctx = lpr.encrypt(x)
	cty = lpr.encrypt(y)

	ctz = lpr.ctmult(ctx,cty)

	answer = lpr.decrypt(ctz)

	print(f'cipher text multiplication')
	print(f'{x} * {y} = {answer}')
	print(f'Multiplication test: { answer == (x*y) }')
	print(f'x == dec(enc(x)): {x == lpr.decrypt(ctx)}')
	print(f'y == dec(enc(y)): {y == lpr.decrypt(cty)}')
	print(f'x+y == dec(enc(x+y)): {x+y == lpr.decrypt(lpr.ctadd(ctx,cty))}')
	return

def test_base_change():
	# this function will test the base changing 
	# function in the lpr() class

	# will first test this with the base as 10
	lpr = LPR(T=2)

	print(f'Public Key[0]:',end='\t')
	lpr.pk[0].polyprint()

	base = lpr.poly_base_change(lpr.pk[0],lpr.q,lpr.T)

	print(f'New polynomials for base change')
	for p in base:
		p.polyprint()

	# recreate the original polynomial using the 
	# power of the different base change

	new = Poly()

	for ind,p in enumerate(base):
		cpy = p.copy()
		for jnd,c in enumerate(cpy):
			cpy[jnd] = c * (lpr.T ** ind)

		new = new + cpy

	print(f'Recovered:', end='\t')
	new = lpr.mod(new)
	new.polyprint()

	print(f'{new == lpr.pk[0]}')

	print(f'q = {lpr.q}')

	return

def test_two_mult():

	#lpr = LPR(t=2**10,q=2**19,T=2*2)
	lpr = LPR()
	print(' ')

	for i in range(10):

		print("testing low multiplication")
		a = 0
		b = 0
		cta = lpr.encrypt(a)
		ctb = lpr.encrypt(b)

		ctc = lpr.ctmult(cta,ctb)

		c = lpr.decrypt(ctc)
		print(f'{a} * {b} = {c}')
		print(f'{(a*b)==c}')

		print('\ntesting high multiplication')
		a = 8
		b = 8
		cta = lpr.encrypt(a)
		ctb = lpr.encrypt(b)

		ctc = lpr.ctmult(cta,ctb)

		c = lpr.decrypt(ctc)
		print(f'{a} * {b} = {c}')
		print(f'{(a*b)==c}')
	return

if __name__ == '__main__':
	#test_base_change()
	#main()
	#test_multiplication()
	test_two_mult()
	pass
