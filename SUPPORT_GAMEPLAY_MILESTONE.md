# Support item gameplay consistency milestone

The capture UI now calls `game_use_support()` rather than mutating inventory and effect timers directly. The shared game logic validates the current encounter screen, inventory quantity, and item index; applies freeze/slow effects (300 frames) or a +25-second timer extension; decrements exactly one item only on successful use; and flags save persistence. The timer extension saturates safely rather than overflowing.

A new host regression test validates invalid calls, empty quantities, effect timers, save flags, and timer overflow protection.

**Limitations:** The support-effect values are inherited from the prototype and have not been verified as faithful to the original game. There is no verified DSi `.nds` build, Black 2/White 2 transfer implementation, or complete original animations.
