# -*- coding:utf-8 -*-

"""
"""


class Delegate:

	daily_forge = 0.
	gift = property(
		lambda obj: obj.share*obj.daily_forge/(obj.vote+obj.cumul-obj.exclude),
		None, None,
		""
	)

	@staticmethod
	def configure(blocktime=8, delegates=51, reward=2):
		assert isinstance(blocktime, int)
		assert isinstance(delegates, int)
		assert isinstance(reward, (float, int))

		Delegate.blocktime = blocktime
		Delegate.delegates = delegates
		Delegate.reward = float(reward)
		Delegate.daily_forge = 24 * 3600./(blocktime*delegates) * reward

	def __init__(self, username, share, vote=0, exclude=0):
		assert 0. < share < 1.

		self.username = username
		self.share = float(share)
		self.vote = vote
		self.exclude = exclude
		self.cumul = 0

	def daily(self, vote):
		return self.share * self.daily_forge * vote/(self.vote+vote-self.exclude)

	def yir(self, vote):
		total = 365 * self.daily(vote)
		return total/vote


def best(*delegates):
	return sorted(delegates, key=lambda d:d.gift, reverse=True)[0]


def reset(*delegates):
	[setattr(d, "cumul", 0) for d in delegates]


def solve(vote, delegates, step=1):
	c = 0
	for c in range(step, vote, step):
		best(*delegates).cumul += step
	best(*delegates).cumul += (vote-c)
	return {d.username:d.cumul for d in delegates}
