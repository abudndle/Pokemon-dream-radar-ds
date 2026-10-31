# Empty-cloud search gameplay correction

This milestone fixes a loss-of-currency and softlock scenario in the portable gameplay code. Basic, Retrieval and Dowsing searches now require at least one cloud before entering radar mode or deducting Dream Orbs. The original source allowed paid cloud searches with zero targets and deducted the cost before creating an empty radar.

The new `tests/test_empty_cloud_search.c` verifies all three no-cloud denials leave state and funds unchanged, and a later paid search consumes the correct cost when a cloud is available.

Verified in this environment: `make test-host test-syntax` passes. The BlocksDS cross compiler is unavailable here, so no bootable `.nds` was built or tested. Do not represent this milestone as complete game compatibility or official Black 2/White 2 transfer support.
