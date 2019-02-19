import sys
import numpy as np
import scipy.optimize as opt

class Symbol(object):
    """
    A class representing a single unit in the boolean SAT problem. This can either refer to an atomic boolean, or a
    constraint based on integer variables
    """
    pass

class Boolean(Symbol):

    def __init__(self, name):
        self.__name = name

    def name(self):
        return self.__name

    def __invert__(self):
        # type: () -> Boolean
        """

        :return:
        """
        return _NegBoolean(self)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name() == other.name()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name())

    def __repr__(self):
        return self.name()

class _NegBoolean(Boolean):

    def __init__(self, symbol):
        self.__symbol = symbol

    def name(self):
        return self.__symbol.name()

    def __invert__(self):
        return self.__symbol

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name() == other.name()
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name(), False)

    def __repr__(self):
        return '~' + self.name()

class Constraint(Symbol):

    def __init__(self, left, right):
        self._left = left
        self._right = right

        if not isinstance(self._right, Constant):
            self._left = Sum(self._left, - self._right)
            self._right = Constant(0)

        # Cluster the symbols on the left
        symbols = {None: 0}
        self.cluster(self._left, symbols)

        # create new left and right
        self._right = Constant(self._right.value() - symbols[None])

        nwterms = []
        for name, mult in symbols.items():
            if name is not None:
                nwterms.append(Integer(name, mult))

        self._left = Sum(*nwterms)

    def cluster(self, term, symbols):

        if isinstance(term, Constant):
            symbols[None] += term.value()
            return

        if isinstance(term, Integer):
            if term.name() not in symbols:
                symbols[term.name()] = 0
            symbols[term.name()] += term.mult()
            return

        if isinstance(term, Sum):
            for subterm in term.terms():
                self.cluster(subterm, symbols)
            return

        raise ValueError('Encountered element {} of type {}. Arithmetic expressions should contain only KB objects or integers.'.format(term, term.__class__))


    def symbol(self):
        return '?'

    def __repr__(self):
        return '[' + str(self._left) + ' ' + self.symbol() + ' ' + str(self._right) + ']'

    def symbols(self):
        '''
        Returns a list of all integer symbols appearing in this constraint
        :return:
        '''

        return union(self._left.symbols(), self._right.symbols())

class GT(Constraint):
    def __init__(self, left, right):
        super(GT, self).__init__(left, right)

    def symbol(self):
        return '>'

    def __invert__(self):
        return LEQ(self._left, self._right)

    def canonical(self):
        """
        Convert to a LEQ relation
        """
        return LEQ(self._right, self._left - 1)

class GEQ(Constraint):
    def __init__(self, left, right):
        super(GEQ, self).__init__(left, right)

    def symbol(self):
        return '>='

    def __invert__(self):
        return LT(self._left, self._right)

    def canonical(self):
        """
        Convert to a LEQ relation
        """
        return LEQ(self._right, self._left)


class LT(Constraint):
    def __init__(self, left, right):
        super(LT, self).__init__(left, right)

    def symbol(self):
        return '<'

    def __invert__(self):
        return GEQ(self._left, self._right)

    def canonical(self):
        """
        Convert to a LEQ relation
        """
        return LEQ(self._left, self._right - 1)


class LEQ(Constraint):
    def __init__(self, left, right):
        super(LEQ, self).__init__(left, right)

    def symbol(self):
        return '<='

    def __invert__(self):
        return GT(self._left, self._right)

    def canonical(self):
        """
        Convert to a LEQ relation
        """
        return self


class EQ(Constraint):
    def __init__(self, left, right):
        super(EQ, self).__init__(left, right)

    def symbol(self):
        return '=='

    def canonical(self):
        """
        The canonical for of an EQ relation is itself.
        """
        return self

# Not used, as it makes the LP problem nonconvex
#
# class NEQ(Constraint):
#     def __init__(self, left, right):
#         super(NEQ, self).__init__(left, right)
#
#     def symbol(self):
#         return '!='
#
#     def __invert__(self):
#         return EQ(self._left, self._right)

class IntSymbol:
    """
    A symbolic expression representing an integer: either an atomic symbol like 'x', a constant
    like 15 or a compound expression like 'x + 15 - y'
    """

    def __lt__(self, other):
        other = self.check(other)
        return LT(self, other)

    def __gt__(self, other):
        other = self.check(other)
        return GT(self, other)

    def __le__(self, other):
        other = self.check(other)
        return LEQ(self, other)

    def __ge__(self, other):
        other = self.check(other)
        return GEQ(self, other)

    def __eq__(self, other):
        other = self.check(other)
        return EQ(self, other)

    # def __ne__(self, other):
    #     other = self.check(other)
    #     return NEQ(self, other)

    def __add__(self, other):
        other = self.check(other)
        return Sum(self, other)
    __radd__ = __add__

    def __sub__(self, other):
        other = self.check(other)
        return Sum(self, - other)
    __rub__ = __sub__


    def check(self, other):
        if not isinstance(other, IntSymbol):
            if isinstance(other, int):
                return Constant(other)
            raise ValueError('You can only use KB objects or ints in comparisons. Encountered: {} {}'.format(other, other.__class__))
        return other


class Sum(IntSymbol):

    def __init__(self, *terms):
        self.__terms = terms
        for term in self.__terms:
            if isinstance(term, int):
                raise ValueError('Unwrapped int {}, {}'.format(term, term.__class__))

        self.__name = ''
        for i, term in enumerate(terms):
            self.__name += ('' if i == 0 else ' + ') + str(term)

    def name(self):
        return self.__name

    def terms(self):
        return self.__terms

    def allterms(self):
        return self.__terms

    def __neg__(self):
        neg_terms = []

        for term in self.__terms:
            neg_terms.append(- term)

        return Sum(*neg_terms)

    def __hash__(self):
        return hash(self.name())

    def __repr__(self):
        return self.__name

    def symbols(self):
        '''
        Returns a set of all integer symbols appearing in this constraint
        :return:
        '''
        return union(*[term.symbols() for term in self.__terms])

class Integer(IntSymbol):

    def __init__(self, name, mult = 1):
        """

        :rtype: object
        """
        self.__name = name
        self.__mult = mult

    def name(self):
        return self.__name

    def mult(self):
        return self.__mult

    def __neg__(self):
        return Integer(self.name(), - self.__mult)

    def __hash__(self):
        return hash(self.name())

    def __mul__(self, other):
        if not isinstance(other, int):
            raise ValueError('Can only multiply number symbol by int.')

        return Integer(self.__name, other)
    __rmul__ = __mul__

    def __repr__(self):
        if self.__mult == 1:
            return self.name()
        if self.__mult == -1:
            return '(-{})'.format(self.name())
        if self.__mult < 0:
            return '({}{})'.format(self.__mult, self.name())
        return '{}{}'.format(self.__mult, self.name())

    def allterms(self):
        '''
        Returns a flat representation of this sum (ie. all elements returned are
        Integers or Constants). May return multiple copies of the same integer if
        the sum has not been simplified.
        :return:
        '''
        result = []
        for term in self.__terms:
            result.extend(term.allterms())

        return result


    def symbols(self):
        return [Integer(self.__name)]

class Constant(Integer):
    """
    An integer with a fixed value
    """
    def __init__(self, value):
        if not isinstance(value, int):
            raise ValueError('Constant should be instantiated with an integer value')

        self.__value = value

    def name(self):
        return str(self.__value)

    def value(self):
        return self.__value

    def __neg__(self):
        return Constant(-self.__value)

    def __hash__(self):
        return hash(self.__value)

    def __repr__(self):
        return self.name()

    def symbols(self):
        return []

    def allterms(self):
        return [self]

class KB(object):
    """
    A class representing a knowledge base.
    """

    def __init__(self):
        self._symbols = []
        self._clauses = []
        self._pos_occurrences = {}
        self._neg_occurrences = {}

    def add_clause(self, *symbols):
        """
        Adds a clause. A clause is a disjunction of atomic symbols or theiur negations. For instance:
        ```
            A = Symbol('A')
            B = Symbol('B')
            C = Symbol('C')

            kb = KB()
            kb.add_clause(A, B, ~C) # A or B or not C
            kb.add_clause(A, ~B)    # A or not B
        ```

        :param symbols:
        :return:
        """

        clause = list(symbols)

        # Check the types of the input
        for elem in clause:
            if not (isinstance(elem, Boolean) or isinstance(elem, Constraint)):
                raise ValueError('Only constraints or boolean values can be part of clauses. Encountered {} of type {}'.format(elem, elem.__class__))

            if isinstance(elem, EQ) and len(clause) != 1:
                raise ValueError(
                    'Equality constraints may only occur in unit clauses (so kb.add_clause(x == 5, y > 3) is not allowed). Encountered clause {}'.format(clause))


        index = len(self._clauses)
        self._clauses.append(clause)

        for symbol in symbols:

            raw_symbol = ~symbol if isinstance(symbol, _NegBoolean) else symbol

            if raw_symbol not in self._symbols:
                self._symbols.append(raw_symbol)

            # Map symbols to the clauses they occur in
            if raw_symbol not in self._neg_occurrences:
                self._neg_occurrences[raw_symbol] = []
            if raw_symbol not in self._pos_occurrences:
                self._pos_occurrences[raw_symbol] = []

            if isinstance(symbol, _NegBoolean):
                self._neg_occurrences[raw_symbol].append(index)
            else:
                self._pos_occurrences[raw_symbol].append(index)

    def satisfiable(self):
        """
        :return: True if there is a way to assign values to the variables in this knowledge base with
            creating inconsistencies.
        """
        first = next(self.models(), None)

        return first is not None

    def models(self, check_theory=True):
        """
        Generator for the models satisfying the current knowledge base
        :return:
        """
        fringe = [_Node(self)]

        while len(fringe) > 0:
            head = fringe.pop()

            if head.consistent():
                if head.finished():
                    # the SAT problem returned a model,
                    # check if the underlying theory is satisfiable
                    sat_model = head.model()

                    if (not check_theory) or is_feasible(sat_model):
                        yield sat_model
                else:
                    fringe.extend(head.children())

    def __repr__(self):
        return 'symbols: {}, clauses {}'.format(self._symbols, self._clauses)

class _Node:
    """
    Node in the KB's search tree.
    """
    __assignments = {}
    __clauses = []
    __kb = None
    __consistent = True

    def __init__(self,
                 kb # type: KB
            ):
        """
        Creates a root node for the given knowledge base
        :param kb:
        """
        self.__kb = kb

        self.__clauses = list(kb._clauses)

    def child(self, symbol, value):
        # type: (Symbol, bool) -> _Node
        """
        Return the node reached by setting the given symbol to the given value
        """

        # Copy the node
        child = _Node(self.__kb)
        child.__assignments = dict(self.__assignments)
        child.__clauses = list(self.__clauses)

        # Perform unit propagation
        nw_assignments = {symbol: value}
        while len(nw_assignments) > 0:
            nw_symbol, nw_value = nw_assignments.popitem()

            # Move the unit clause to the assignments
            child.__assignments[nw_symbol] = nw_value

            # Rewrite the knowledge base with the new information
            for index in child.__kb._pos_occurrences[nw_symbol]:
                if nw_value:
                    child.__clauses[index] = None # Remove the clause
                else:
                    # Remove the symbol from the clause
                    if child.__clauses[index] is not None: # Clause was already removed earlier

                        clause = list(child.__clauses[index])
                        clause.remove(nw_symbol)

                        if len(clause) == 0: # Empty clauses indicates inconsistency
                            child.__consistent = False
                            return child

                        if len(clause) == 1: # New unit clause created
                            s = clause[0]
                            if isinstance(s, _NegBoolean):
                                nw_assignments[~ s] = False
                            else:
                                nw_assignments[s] = True
                            child.__clauses[index] = None

                        child.__clauses[index] = clause

            for index in self.__kb._neg_occurrences[nw_symbol]:
                if nw_value:
                    # Remove the symbol from the clause
                    if child.__clauses[index] is not None: # Clause was already removed earlier

                        clause = list(child.__clauses[index])
                        clause.remove(~ nw_symbol)

                        if len(clause) == 0: # Empty clauses indicates inconsistency
                            child.__consistent = False
                            return child

                        if len(clause) == 1: # New unit clause created
                            s = clause[0]
                            if isinstance(s, _NegBoolean):
                                nw_assignments[~ s] = False
                            else:
                                nw_assignments[s] = True
                            child.__clauses[index] = None

                        child.__clauses[index] = clause
                else:
                    child.__clauses[index] = None # Remove the clause

        return child

    def children(self):
        if not self.consistent():
            return []

        next_symbol = next(self.free(), None)
        if not next_symbol:
            return []

        return self.child(next_symbol, True), self.child(next_symbol, False)

    def free(self):
        for symbol in self.__kb._symbols:
            if symbol not in self.__assignments:
                yield symbol

    def consistent(self):
        return self.__consistent

    def finished(self):
        """
        :return: True if the current node represents a complete model, with all symbols
        assigned definite values.
        """
        return len(self.__kb._symbols) == len(self.__assignments.keys())

    def model(self):
        if not self.finished():
            return None
        else:
            return self.__assignments

    def __repr__(self):
        return str(self.__assignments) + (' finished' if self.finished() else ' incomplete') \
               + ' ' + (' consistent' if self.consistent() else ' inconsistent') \
               + ', clauses:' + str(self.__clauses)

def optimize(*constraints):
    """
    Minimizes the given set of symbols under the given linear arithmetical constraints
    :param constraint:
    :return:
    """

    # Gather all symbols
    symbols = union(*[c.symbols() for c in constraints])
    symbols = [s.name() for s in symbols]
    n = len(symbols)

    # Canonicalize the constraints, and sort by equalities ad inequalities
    equalities = []
    inequalities = []

    for constraint in constraints:
        canonical = constraint.canonical()
        if isinstance(canonical, LEQ):
            inequalities.append(canonical)
        elif isinstance(canonical, EQ):
            equalities.append(canonical)
        else:
            raise ValueError('Encountered constraint that did not canonize to LEQ or EQ: {}, canonical class {}'.format(canonical, canonical.__class__))

    # Create matrices, add constraints
    A_ub = np.zeros((len(inequalities), len(symbols)))
    A_eq = np.zeros((len(equalities), len(symbols)))

    b_ub = np.zeros((len(inequalities)))
    b_eq = np.zeros((len(equalities)))

    c = np.ones((len(symbols)))

    for i, constraint in enumerate(inequalities):
        b_ub[i] = constraint._right.value()

        for term in constraint._left.allterms():
            if not isinstance(term, Constant):
                name = term.name()
                mult = term.mult()
                j = symbols.index(name)

                A_ub[i, j] += mult
            else:
                raise ValueError('Unexpected state: the left part of a constraint should not contain constants.')

    for i, constraint in enumerate(equalities):
        b_eq[i] = constraint._right.value()

        for term in constraint._left.allterms():
            if not isinstance(term, Constant):
                symbol = term.name()
                mult = term.mult()
                j = symbols.index(symbol)

                A_eq[i, j] += mult
            else:
                raise ValueError(
                    'Unexpected state: the left part of a constraint should not contain constants.')

    result = opt.linprog(c, A_ub, b_ub, A_eq, b_eq, bounds = [(None, None)] * n)

    return result


def is_feasible(model):

    constraints = []
    for symbol, value in model.items():
        if isinstance(symbol, Constraint):
            if value:
                constraints.append(symbol)
            else:
                if isinstance(symbol, EQ):
                    raise ValueError('Something went wrong. The SAT solver should not assign False to EQ constraints. Encountered model {}.'.format(model))
                constraints.append(~ symbol)
    if len(constraints) == 0:
        return True

    return optimize(*constraints).status != 2

def union(*lists):
    '''
    We can't store the Integer objects in sets, because we overwrote __eq__. So we'll store them
     in lists instead, and do unions this way.
    :param lists: Lists cotaining integers and constants
    :return:
    '''
    result = []
    seen = set()

    for list in lists:
        for symbol in list:
            if symbol.name() not in seen:
                seen.add(symbol.name())
                result.append(symbol)

    return result
