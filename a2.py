# CMPUT 455 Assignment 2 starter code
# This is a sample solution for assignment 1.
# Implement the new commands to complete the assignment
# Full assignment specification and game rules on Canvas

import ast
import random
from sys import stderr
from typing import Any, Callable, Dict, List, Optional, Tuple

# My import(s)
import time

# ---------------------------------------------------------------------------
# Assignment restrictions (see assignment page)
# ---------------------------------------------------------------------------
MIN_HEAPS = 1
MAX_HEAPS = 20
MIN_TOKENS = 1
MAX_TOKENS = 20
MIN_VALUE = 1
MAX_VALUE = 20
KOMI_LIMIT = 100  # -100 < komi < 100, and komi must be an integer + 0.5

# The time limit, in seconds, for a single solve or genmove command
MIN_TIMELIMIT = 1
MAX_TIMELIMIT = 100
DEFAULT_TIMELIMIT = 1

BLACK = 'b'
WHITE = 'w'
COLORS = (BLACK, WHITE)

Token = Tuple[str, int]
Heap = List[Token]
Heaps = List[Heap]

# ------------------------------------------------------------------------------------------------------ #
# Section for global vars I need + SearchTimeout()
# ------------------------------------------------------------------------------------------------------ #

# check the clock every 256 nodes to det if at time limit
#   -> stored in hex so I can do bitwise AND of node_count with 11111111
#   -> how I will check time only once every 256 nodes cuz 256 = 1 00000000 and bitwise and gives all 0s
TIME_CHECK_MASK = 0xFF

NINF = float("-inf")
INF = float("inf")
    
# flags for the tt
EXACT, LOWER, UPPER = 0, 1, 2

class SearchTimeout(Exception):
    """
    Raised internally when the current solve/genmove time limit is crossed.
    """
    pass

# ------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------ #

def not_yet() -> bool:
    raise NotImplementedError("Command not implemented.")
    return False


def print_error(error: str) -> None:
    print(error, file=stderr)


def opponent(color: str) -> str:
    return WHITE if color == BLACK else BLACK


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def is_int(obj: Any) -> bool:
    # bool is a subclass of int; True/False are not valid values
    return isinstance(obj, int) and not isinstance(obj, bool)


def is_token(obj: Any) -> bool:
    return (isinstance(obj, tuple)
            and len(obj) == 2
            and obj[0] in COLORS
            and is_int(obj[1])
            and MIN_VALUE <= obj[1] <= MAX_VALUE)


def is_heap(obj: Any) -> bool:
    return (isinstance(obj, list)
            and MIN_TOKENS <= len(obj) <= MAX_TOKENS
            and all(is_token(token) for token in obj))


def is_heaps(obj: Any) -> bool:
    return (isinstance(obj, list)
            and MIN_HEAPS <= len(obj) <= MAX_HEAPS
            and all(is_heap(heap) for heap in obj))


def parse_komi(text: str) -> Optional[float]:
    try:
        komi = float(text)
    except ValueError:
        return None
    if not (-KOMI_LIMIT < komi < KOMI_LIMIT):
        return None
    if (komi - 0.5) != int(komi - 0.5):
        return None
    return komi


def parse_heaps(text: str) -> Optional[Heaps]:
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None
    if not is_heaps(parsed):
        return None
    return parsed


def parse_heap_number(args: str) -> Optional[int]:
    parts = args.split()
    if len(parts) != 1:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class HeapGo:
    def __init__(self, komi: float, heaps: Heaps) -> None:
        self.komi = komi
        self.heaps = heaps
        self.toplay = BLACK
        self.score = {BLACK: 0, WHITE: komi}

    def __str__(self) -> str:
        return "k {} {}".format(self.komi, self.heaps)

    def is_legal(self, heap_number: int) -> bool:
        return 0 <= heap_number < len(self.heaps) and len(self.heaps[heap_number]) > 0

    def legal_moves(self) -> List[int]:
        return [i for i in range(len(self.heaps)) if self.is_legal(i)]

    def game_over(self) -> bool:
        return len(self.legal_moves()) == 0

    def play(self, heap_number: int) -> bool:
        if not self.is_legal(heap_number):
            return False
        heap = self.heaps[heap_number]
        gained = 0
        # Rule 1: take all own-color tokens from the top
        while heap and heap[-1][0] == self.toplay:
            gained += heap.pop()[1]
        # Rule 2: then one opponent token, if any remain
        if heap:
            gained += heap.pop()[1]
        self.score[self.toplay] += gained
        self.toplay = opponent(self.toplay)
        return True

    def winner(self) -> Optional[str]:
        if not self.game_over():
            return None
        if self.score[BLACK] > self.score[WHITE]:
            return BLACK
        if self.score[WHITE] > self.score[BLACK]:
            return WHITE
        return None  # draw; impossible with komi = integer + 0.5


CommandMap = Dict[str, Callable[[str], bool]]


class CommandInterface:
    def __init__(self) -> None:
        self.game: Optional[HeapGo] = None
        self.timelimit = DEFAULT_TIMELIMIT
        # you can add your own initialisation here

        # ------------------------------------------------------------------------------------------------------ #
        # ------------------------------------------------------------------------------------------------------ #
        # Adding a transposition table to map tuple -> tuple [(heaps, toplay) -> (value, flag)]
        # It's gonna be kept for the whole program (not reset after each game) cuz the entries can be used 
        # and are valid for ANY game.
        
        self.tt: Dict[Tuple[Any, str], Tuple[float, int]] = {}
        self._deadline = 0.0
        self._node_count = 0
        # ------------------------------------------------------------------------------------------------------ #
        # ------------------------------------------------------------------------------------------------------ #

        self.commands: CommandMap = {
            "help": self.cmd_help,
            "heapgo": self.cmd_heapgo,
            "show": self.cmd_show,
            "toplay": self.cmd_toplay,
            "play": self.cmd_play,
            "legal": self.cmd_legal,
            "genmove": self.cmd_genmove,
            "score": self.cmd_score,
            "winner": self.cmd_winner,
            "solve": self.cmd_solve,
            "timelimit": self.cmd_timelimit,
            }

    # ------------------------------------------------------------------------------------------------------ #
    # ------------------------------------------------------------------------------------------------------ #
    # HELPER FUNCTIONS I NEED TO ADD: they need to be inside CommandInterface that's why they r here.
    # ------------------------------------------------------------------------------------------------------ #
    # ------------------------------------------------------------------------------------------------------ #
    def _check_time(self) -> None:
            """
            _check_time: checks whether the solver has exceeded its search time limit.
    
            Search calls this func once per node visited, but the clock is actually only
            checled every 256 nodes to avoid overhead.
                -> every node is still counted, but the clock is not ALWAYS checked.
            
            Returns/Outputs:
                SearchTimeout: raises this if the current time has reached or passed the search deadline
            """
            # track nodes visited
            self._node_count += 1
    
            # Check time every 256 nodes
            if (self._node_count & TIME_CHECK_MASK) == 0:
                # perf_counter gives the most accurate timer
                if time.perf_counter() >= self._deadline:
                    raise SearchTimeout()
    
    
    @staticmethod
    def _play_heap(heap: Tuple[Token, ...], color: str) -> Tuple[int, Tuple[Token, ...]]:
        """
        _play_heap(): applies the Heap Go move rule to one heap for the player = color.
            -> Remove all consecutive tokens of own color, then one oponent token if applicable
    
        Input(s):
            heap: the tuple containing the current heap, bottom to top
            color: b or w depedning on who is currently playing
            
        Returns/Outputs:
            A tuple containing (tokens gained, new heap), where new heap is a tuple.
        """
        # convert heap tuple to a list so we can pop()
        tokens = list(heap)
        gained = 0

        # 1. Remove all consecutive tokens of own kind (tokens[-1] is the top):
        while tokens and tokens[-1][0] == color:
            # [1] to return the score from ("c", p) where p is points
            gained += tokens.pop()[1]

        # 2. One opponent token if possible
        if tokens:
            gained += tokens.pop()[1]

        # Convert the remaining list back into a tuple to return as a new heap
        #   -> Also the game state is immutable again and can then be used as the tt keys
        return gained, tuple(tokens)


    def _generate_moves(self, heaps: Tuple[Tuple[Token, ...], ...], toplay: str) -> List[Tuple[int, int, Tuple[Tuple[Token, ...], ...]]]:
        """
        _generate_moves(): generates all legal moves from the current game position.

        A legal move = choosing any non-empty heap and applying the Heap Go move rule to that heap. For each possible move, store:
            1. The num of the heap being played
            2. The num of points gained from that move
            3. The complete game state after the move
        
        The resulting moves are sorted by points (decreasing), which will help alpha-beta pruning
        find good moves and cut off bad branches earlier.

        Input(s):
            heaps: the current collection of heaps
            toplay: b/w depending on whose turn it is
        
            Returns/Outputs: a list of tuples in the form (heap num, points gained, resulting heaps)
                -> sorted from the largest points gained to the least.
        """
        # Store every legal move generated from the current position
        moves = []

        # enumerate will give:
        #   i = heap's index/num
        #   heap = contents of heaps[i]
        for i, heap in enumerate(heaps):
            # skip empty heaps and call the previous function to get vals
            if heap:
                gained, new_heap = self._play_heap(heap, toplay)

                # construct the complete game state after playing heap i
                #   -> basically just replace heap i, keep heaps before i (:i) and after i (i:) the same
                #   -> make a tuple of heaps (heap[i]) with (new_heap,) to match the format of the others
                new_heaps = heaps[:i] + (new_heap,) + heaps[i + 1:]
                moves.append((i, gained, new_heaps))

        # Sort by gained (m[1]) and return
        moves.sort(key = lambda m: m[1], reverse = True)
        return moves


    def _negamax(self, heaps: Tuple[Tuple[Token, ...], ...], toplay: str, alpha: float, beta: float) -> float:
        """
        _negamax(): returns the best achievable (own future score - opponent future score) for player toplay, calculated
        for the rest of the game starting from current heaps and best play. 
            -> A position is a win for toplay iff the value, added to the current score difference, is > 0.
            -> Else value < 0 and is a loss
        
        Current scores are NOT included here, they're handled by the caller so that the same game position can
        be reused regardless of the scores already collected.

        Of all my possible moves, keep the one with the greatest eventual score difference.

        Input(s):
            heaps: the current collection of heaps
            toplay: b/w depending on whose turn it is
            alpha: min gurantee for current player, from previously explored branches
            beta: the value the OPP has already guaranteed elsewhere, so if this branches's best reaches beta, they'll avoid it. 
                -> Prune cuz opp forces a val <= alpha.
        
            Returns/Outputs: the best achievable future score difference for player toplay
        """
        # use helper functions
        self._check_time()
        moves = self._generate_moves(heaps, toplay)

        # No legal moves
        if not moves: return 0

        # sort heaps to give equivelant pos's same representation -> shared entry in the tt
        #   -> tt uses the tuplw (heaps, toplay) as the key, so I will put it into that form
        key = (tuple(sorted(heaps)), toplay)
        entry = self.tt.get(key)

        # save the original alpha val to determine the right transposition table flag (alpha can be updated when a cached lower bound is found)
        original_alpha = alpha

        if entry is not None:
            val, flag = entry

            # a EXACT entry (0) contains the exact val of this position, so no need to search again
            if flag == EXACT: return val

            # A LOWER bound -> true value is at least val. If better than curr alpha bound, raise alpha
            elif flag == LOWER:
                if val > alpha:
                    alpha = val

            # An UPPER bound -> true value is at most val. If smaller than current beta bound, lower beta
            elif flag == UPPER:
                if val < beta:
                    beta = val

            # If alpha has already reached or passed beta, the cached info already proves this branch cannot affect the result
            if alpha >= beta: return val

        # start with the wc = -inf
        best = NINF

        # Examine every legal move (i is the heap number)
        for (_i, gained, new_heaps) in moves:
            # After making this move, the opp becomes toplay
            #   -> recursive call evaluates from opp's perspective.
            #   -> if opp's future val is x, then ours is gained - x
            #   -> alpha-beta window must be shifted by gained s.t alpha <= gained - child_val = OUR VALUE <= beta which = gained - beta <= child_val <= gained - alpha
            val = gained - self._negamax(new_heaps, opponent(toplay), gained-beta, gained-alpha)

            # Keep the best move found so far, and update alpha if we found a better guaranteed value
            if val > best: best = val
            if best > alpha: alpha = best

            # If alpha reaches beta, the rest of the moves don't need to be computed bc the opp has a move that makes this branch irrelevant
            if alpha >= beta: break

        # If best val never exceeded og alpha, the search established an upper bound instead of an exact val.
        # If it reached or exceeded bets, then it's a lower bound. O.W, the complete search window was searched and best is the exact val of the position
        if best <= original_alpha:
            flag = UPPER
        elif best >= beta:
            flag = LOWER
        else:
            flag = EXACT

        # Save the result so that the same position cvan be used later
        self.tt[key] = (best, flag)
        return best


    def _negamax_root(self, heaps: Tuple[Tuple[Token, ...], ...], toplay:str, deadline: float) -> Tuple[float, Optional[int]]:
        """
        _negamax_root():searches the current position and returns its best value and move. Does the 
        same score difference calculation as _negamax(), but also keeps track of WHICH heap produces
        the best val so that the caller can actually make that move.

        Input(s):
            heaps: current collection of heaps
            toplay: b/w depending on whose turn it is
            deadline: time which the search must stop

        Returns/Outputs: a tuple containing (the best achievable score difference, i), where i is the heap that yields the score
            -> If there are no legal moves, return (0, None)
        """
        # Start the deadline so that _check_time() can access it during the recursive search + node count + moves
        self._deadline = deadline
        self._node_count = 0
        moves = self._generate_moves(heaps, toplay)

        # No legal moves = no remaining score for the game
        if not moves: return 0, None

        # Start with WC value and use the first legal moce as the INIT best move (so we have a valid heap b4 loop begins)
        best = NINF
        best_move = moves[0][0]

        # At the root, there are no restrictions on the possible value, so alpha and beta = -/+ inf
        alpha, beta = NINF, INF

        # try every possible first move
        for (i, gained, new_heaps) in moves:
            # eval this move using the same negamax calc as the recursive search
            val = gained - self._negamax(new_heaps, opponent(toplay), gained-beta, gained-alpha)

            # If this moce is better than every moce considered so far, remember both its val and its heap num
            if val > best:
                best = val
                best_move = i

            # update alpha because best is the best value we can currently GUARANTEE at the root
            if best > alpha:
                alpha = best

        return best, best_move


    def _heaps_tuple(self) -> Tuple[Tuple[Token, ...], ...]:
        """
        _heaps_tuple(): returns the current game heaps as immutable tuples.
            -> Game object stores its heaps in mutable containers, while
            the solver represents game states using tuples. Converting the heaps
            to tuples allows them to be safely snd reliably used as keys for the tt.
        
        _heaps_tuple() -> get current game state -> _negamax_root() -> try heaps -> _negamax()

        Input(s): N/A

        Outputs/Returns: a tuple containing one tuple for each current heap (tuple of tuples)
        """
        # Make sure a game has actually been started b4 trying to access
        assert self.game is not None

        # convert every individual heap into a tuple, then convert the outer collection of heaps into a tuple as well
        # result = ( (token, token, ...), (token, ...), ...)
        return tuple(tuple(heap) for heap in self.game.heaps)


# ------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------ #
# END OF MY HELPERS
# ------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------ #


#============================================================================
# Command implementations
#============================================================================
    def cmd_heapgo(self, args: str) -> bool:
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            print_error("usage: heapgo komi game")
            return False
        komi = parse_komi(parts[0])
        if komi is None:
            print_error("invalid komi: {}".format(parts[0]))
            return False
        heaps = parse_heaps(parts[1])
        if heaps is None:
            print_error("invalid game: {}".format(parts[1]))
            return False
        self.game = HeapGo(komi, heaps)
        return True

    def cmd_show(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        print(self.game)
        return True

    def cmd_toplay(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        if args not in COLORS:
            print_error("invalid color: {}".format(args))
            return False
        self.game.toplay = args
        return True

    def cmd_play(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        heap_number = parse_heap_number(args)
        if heap_number is None:
            print_error("invalid heap number: {}".format(args))
            return False
        if not self.game.play(heap_number):
            print_error("illegal move: {}".format(heap_number))
            return False
        return True

    def cmd_legal(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        heap_number = parse_heap_number(args)
        if heap_number is None:
            print_error("invalid heap number: {}".format(args))
            return False
        print("yes" if self.game.is_legal(heap_number) else "no")
        return True

# ------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------ #
# MODIFY cmd_genmove() HERE
# ------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------ #
    def cmd_genmove(self, args: str) -> bool:
        """
        cmd_genmove(): generate and play a move for the current player. The solver is used to find a winning move when possible.
            -> If solver det's current player cannot force a win or if the search time runs out, choose a random legal move instead.

        Outputs/Returns: True if a legal moce was successfully played, False o.w
        """
        if self.game is None:
            print_error("no game started")
            return False
        moves = self.game.legal_moves()
        if not moves:
            print_error("no legal moves")
            return False
        # you need to replace this random move by a move from your solver

        # remember the current player and their opp
        toplay = self.game.toplay
        opp = opponent(toplay)

        # start with no chosen move, will be replaced weith heap i if the solcer later finds a winning move
        chosen_move: Optional[int] = None

        # convert the curretn mutable game heaps into the immutable tuple representation using helper
        heaps = self._heaps_tuple()
        deadline = time.perf_counter() + self.timelimit # = absolute time the search must stop (now + timelimit)

        try:
            # Search for the best move from the current position
            value, best_move = self._negamax_root(heaps, toplay, deadline)

            # Solver's val only includes future points, include the score difference that already exists here
            current_diff = self.game.score[toplay] - self.game.score[opp]
            total_diff = current_diff + value

            # use current player's best move if they can finish with a + scre difference
            if total_diff > 0: chosen_move = best_move

        except SearchTimeout:
            # Solver didn't finish b4 deadline, cannot rely on its result. Choose random legal move instead (already implemented in starter code below)
            chosen_move = None

        if chosen_move is None:
            move = random.choice(moves)
            
        self.game.play(move)
        print(move)
        return True

# ------------------------------------------------------------------------------------------------------ #
# ------------------------------------------------------------------------------------------------------ #

    def cmd_score(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        print("b {} w {}".format(self.game.score[BLACK], self.game.score[WHITE]))
        return True

    def cmd_winner(self, args: str) -> bool:
        if self.game is None:
            print_error("no game started")
            return False
        winner = self.game.winner()
        if winner is None:
            print_error("game not over" if not self.game.game_over() else "draw")
            return False
        print(winner)
        return True

#============================================================================
# You need to implement the following methods.
#============================================================================
    """
    The total value of ALL tokens (in heaps + already scored) is an invariant -> max(own score) = max(own final score - opponent final score)
        -> Search for a single numeric value (own score - opp score) -> negamax will returen this
        -> Can ignore already collected scores: just need current lead/loss and the solver finds how much better/worse the remaining game is for the player
        -> Because of above I think we can reuse vals stored in the tt will try this way then see
    
    DP: V(position) = max(points gained now - V(position after move)) for all legal moves at position with V(0) = 0
            
    TODO:
        1. Find moves u can make
        2. Evaluate resulting positions (gain)
        3. Get opponent's best value (loss)
        4. Take max(gain-loss) and eventually the best future difference
    """
    
    def cmd_solve(self, args: str) -> bool:
        """
        cmd_solve: tries to compute the winner of the current Heap Go position, assuming perfect play by both b and w.
            -> If the player to move can win, print their best move (heap to play)
            -> O.W print opp
        """
        # Check for active game b4 trying to solve a position
        if self.game is None:
            print_error("no game started")
            return False

        # remember the player whose turn it is and their opp
        toplay = self.game.toplay
        opp = opponent(toplay)

        # Normally, solve is only called on an active game, but I'll handle a finished game too just in case
        if self.game.game_over():

            # winner() returns the winning color (or none for a drawe)
            winner = self.game.winner()
            if winner is None:
                print_error("draw")
                return False

            print(winner)
            return True

        # convert the curretn mutable game heaps into the immutable tuple representation using helper
        #   -> used by the solver and tt
        heaps = self._heaps_tuple()
        deadline = time.perf_counter() + self.timelimit # = absolute time the search must stop (now + timelimit)

        # run negamax from the current position (if search runs out of time, cmd_solve cannot give a completed sol -> report failure)
        try:
            value, best_move = self._negamax_root(heaps, toplay, deadline)
        except SearchTimeout:
            return False

        # _negamax_root() only evals points that can still be earned in the future (gives (value, best_move)), 
        # so we add the score difference that already exists in the current game here.
        current_diff = self.game.score[toplay] - self.game.score[opp]
        total_diff = current_diff + value

        # Decide if player toplay can win
        if total_diff > 0:
            print("{} {}".format(toplay, best_move))
        else:
            print(opp)

        return True

    def cmd_timelimit(self, args: str) -> bool:
        """
        cmd_timelimit(): sets the max amount of time allowed for a solver search

        Input(s):
            args: the command arguments, espected to contain one int representing the time limit in secs.
        
            Outputs/Returns: True if the time limit was successfully set, False o.w
        """
        # Split arg so we can check if exactly 1 val was given
        parts = args.split()
        if len(parts) != 1:
            print_error("useage: timelimit seconds")
            return False

        # convert the arg from a string into a integer and handle errosd
        try:
            seconds = int(parts[0])
        except ValueError:
            # not a valid integer
            print_error("invalid timelimit: {}".format(args))
            return False

        # make sure the requested time is within the allowed range
        if not (MIN_TIMELIMIT <= seconds <= MAX_TIMELIMIT):
            print_error("timelimit out of range: {}".format(args))
            return False

        # Store the valid time limit so the solver can use it later and return True
        self.timelimit = seconds
        return True

    
#============================================================================
# End of functions requiring implementation
#============================================================================

#============================================================================
# The code below should not need modification
# Anyway, you may change or add to this code as you see fit
#============================================================================
    def cmd_help(self, ignore_args: str) -> bool:
        print("\nKnown commands:")
        for cmd in self.commands:
            print(cmd)
        return True

    def process_command(self, cmd_name: str, cmd_args: str) -> None:
        status = "= -1"
        cmd = self.commands.get(cmd_name)
        if cmd:
            try:
                if cmd(cmd_args):
                    status = "= 1"
            except Exception as e:
                print_error(f"Command {cmd_name} with arguments {cmd_args} failed with exception: {e}")
        else:
            print_error("Unknown command. Type 'help' for commands.")
        print(status)

    def main_loop(self) -> None:
        process_commands = True
        while process_commands:
            try:
                line = input()
            except EOFError:
                break
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            cmd_name = parts[0]
            if cmd_name == "exit":
                process_commands = False
                continue
            cmd_args = parts[1] if len(parts) > 1 else ""
            self.process_command(cmd_name, cmd_args)


if __name__ == "__main__":
    interface = CommandInterface()
    interface.main_loop()
