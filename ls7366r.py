# The MIT License (MIT)
#
# Copyright (c) 2018 Carter Nelson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# MDR0 configuration data - the configuration byte is formed with
# single segments taken from each group and ORing all together.

# Parsko's additions
#	The proper way to read the counter is to load the OTR register,
#   then read the register.  It is possible to lose counts if reading
#   the CNTR register while still counting edges.  With very low resolution
#   encoders at low speeds, this may be okay.  But, high speed/high res
#   encoders can loose counts, which will accumulate over time.
#   Ex.  OK - https://www.adafruit.com/product/377 - 24 count/rev
#   Ex.  Probably okay - 400 count/rev disk (1600 count/rev post quad)
#   Ex.  I'd like to know - 5000 count/rev disk, 20000 post quad
#   EX.  Unproven/questionable - Renishaw Vionic 50nm/ct at 300mm/sec
#   This library is written to load the count to the OTR, then read that

COUNTER_BITS = (32, 24, 16, 8)
QUADRATURE_MODES = (0, 1, 2, 4)

# Count modes
NQUAD = 0x00          # non-quadrature mode
QUADRX1 = 0x01        # X1 quadrature mode
QUADRX2 = 0x02        # X2 quadrature mode
QUADRX4 = 0x03        # X4 quadrature mode

# Running modes
FREE_RUN = 0x00
SINGE_CYCLE = 0x04
RANGE_LIMIT = 0x08
MODULO_N = 0x0C

# Index modes
DISABLE_INDX = 0x00   # index_disabled
INDX_LOADC = 0x10     # index_load_CNTR
INDX_RESETC = 0x20    # index_rest_CNTR
INDX_LOADO = 0x30     # index_load_OL
ASYNCH_INDX = 0x00    # asynchronous index
SYNCH_INDX = 0x80     # synchronous index

# Clock filter modes
FILTER_1 = 0x00       # filter clock frequncy division factor 1
FILTER_2 = 0x80       # filter clock frequncy division factor 2

# MDR1 configuration data; any of these
# data segments can be ORed together

# Flag modes
NO_FLAGS = 0x00       # all flags disabled
IDX_FLAG = 0x10       # IDX flag
CMP_FLAG = 0x20       # CMP flag
BW_FLAG = 0x40        # BW flag
CY_FLAG = 0x80        # CY flag

# 1 to 4 bytes data-width
BYTE_4 = 0x00         # four byte mode
BYTE_3 = 0x01         # three byte mode
BYTE_2 = 0x02         # two byte mode
BYTE_1 = 0x03         # one byte mode

# Enable/disable counter
EN_CNTR = 0x00        # counting enabled
DIS_CNTR = 0x04       # counting disabled

# LS7366R op-code list
CLR_MDR0 = 0x08  # 0000_1000
CLR_MDR1 = 0x10  # 0001_0000
CLR_CNTR = 0x20  # 0010_0000
CLR_STR = 0x30   # 0011_0000
READ_MDR0 = 0x48 # 0100_1000
READ_MDR1 = 0x50 # 0101_0000
READ_CNTR = 0x60 # 0110_0000
READ_OTR = 0x68  # 0110_1000
READ_STR = 0x70  # 0111_0000
WRITE_MDR1 = 0x90# 1001_0000
WRITE_MDR0 = 0x88# 1000_1000
WRITE_DTR = 0x98 # 1001_1000
LOAD_CNTR = 0xE0 # 1110_0000
LOAD_OTR = 0xE8  # 1110_1000 CATER says E4, off by one bit

class circuitpython_LS7366R():
	
	"""LSI/CSI LS7366R quadrature counter."""

	def __init__(self, device):#spi, cs):
		# This should be a circuitpython busio compatible object.
		self._spi = device
		
		self.counter_bit_setting = 32
		self.bits = self.counter_bit_setting

		print(str(self.counts))
		
		# Default config
		self._write_mdr0(QUADRX4 | FREE_RUN | DISABLE_INDX | FILTER_1)
		self._write_mdr1(BYTE_4 | EN_CNTR)

		# Set to zero at start
		self.counts = 0
		

	@property
	def counts(self):
		"""Current counts as signed integer."""
		return self._get_counts()

	@counts.setter
	def counts(self, value):
		self._set_counts(value)

	@property
	def bits(self):
		"""Counter bits."""
		return COUNTER_BITS[self._read_mdr1()[0] & 0x03]

	@bits.setter
	def bits(self, value):
		if value not in COUNTER_BITS:
			raise ValueError("Bits must be one of ", *COUNTER_BITS)
		self.counter_bit_setting = COUNTER_BITS.index(value)
		self._write_mdr1(self._read_mdr1()[0] &0xFC | COUNTER_BITS.index(value))
		return value
		
	@property
	def quadrature(self):
		"""Quadrature mode."""
		return QUADRATURE_MODES[self._read_mdr0()[0] & 0x03]

	@quadrature.setter
	def quadrature(self, value):
		if value not in QUADRATURE_MODES:
			raise ValueError("Mode must be one of ", *QUADRATURE_MODES)
		self._write_mdr0((self._read_mdr0()[0] & 0xFC) | QUADRATURE_MODES.index(value))

	def _get_counts(self, ):
		"""Read the counter register value."""      
		#bits = self.counter_bit_setting  #PARSKO-I didn't like the unnecessary
		#                                   double read.  I made this a var
		# byte_values = self._read_cntr()
		byte_values = self._read_counter()
		hex_result_raw = ["".join("{:02x}".format(x) for x in byte_values[1:])]
		dec = int(hex_result_raw[0],16)
		if dec > 2**31:
			dec -= 2**32
		return dec

	def _set_counts(self, value):
		"""Set the counter register value."""
		self._write_dtr(value)
		self._load_cntr()

	def _clear_mdr0(self):
		"""Clear MDR0."""
		with self._spi as bus_device:
			bus_device.write([CLR_MDR0])

	def _clear_mdr1(self):
		"""Clear MDR1."""
		with self._spi as bus_device:
			bus_device.write([CLR_MDR1])

	def _clear_cntr(self):
		"""Clear the counter."""
		with self._spi as bus_device:
			bus_device.write([CLR_CNTR])

	def _clear_str(self):
		"""Clear the status register."""
		with self._spi as bus_device:
			bus_device.write([CLR_STR])

	def _read_mdr0(self):
		"""Read the 8 bit MDR0 register."""
		return self._spi.xfer2([READ_MDR0, 0x00])[1:]

	def _read_mdr1(self):
		"""Read the 8 bit MDR1 register."""
		# return self._spi.xfer2([READ_MDR1, 0x00])[1:]
		mdr1_response = bytearray(5)
		with self._spi as bus_device:
			bus_device.write_readinto(bytes([READ_MDR1, 0x00, 0x00, 0x00, 0x00]),mdr1_response)	
		mdr1_response = mdr1_response[1:]
		return mdr1_response

	def _read_cntr(self):
		"""Transfer CNTR to OTR, then read OTR. Size of return depends
		   on current bit setting."""
		#return self._spi.xfer2([READ_CNTR]+[0]*(self.counter_bit_setting//8))[1:]
		cntr_response = bytearray(5)
		with self._spi as bus_device:
			bus_device.write_readinto(bytes([READ_CNTR, 0x00, 0x00, 0x00, 0x00]),cntr_response)
		cntr_response = cntr_response[1:]
		return cntr_response 
	
	def _read_counter(self):
		# PARSKO
		"""Transfer CNTR to OTR, then read OTR. Size of return depends
		   on current bit setting."""
		self._load_otr()
		# print('c')
		return self._read_otr()

	def _read_otr(self):
		"""Output OTR."""
		# return self._spi.xfer2([READ_OTR]+[0]*(self.bits//8))[1:]
		with self._spi as bus_device:
			otr_response = bytearray( 5 )
			bus_device.write_readinto(bytes([READ_CNTR,0x00,0x00,0x00,0x00]),otr_response,in_start=0)
		return otr_response

	def _read_str(self):
		"""Read 8 bit STR register."""
		# return self._spi.xfer2([READ_STR,0x00])[1:]
		with self._spi as bus_device:
			str_response = bytearray( 5 )
			bus_device.write_readinto(bytes([READ_STR,0x00]), str_response)

	def _write_mdr0(self, mode):
		"""Write serial data at MOSI into MDR0."""
		with self._spi as bus_device:
			bus_device.write(bytes([WRITE_MDR0, mode]))

	def _write_mdr1(self, mode):
		"""Write serial data at MOSI into MDR1."""
		with self._spi as bus_device:
			bus_device.write(bytes([WRITE_MDR1, mode]))

	def _write_dtr(self, value):
		"""Write to 32 bit DTR register."""
		with self._spi as bus_device:
			bus_device.write(bytes([WRITE_DTR, value >> 24 & 0xFF,
										 value >> 16 & 0xFF,
										 value >>  8 & 0xFF,
										 value       & 0xFF]))

	def _load_cntr(self):
		"""Transfer DTR to CNTR."""
		with self._spi as bus_device:
			bus_device.write(bytes([LOAD_CNTR]))

	def _load_otr(self):
		"""Transfer CNTR to OTR."""
		with self._spi as bus_device:
			bus_device.write(bytes([LOAD_OTR]))
