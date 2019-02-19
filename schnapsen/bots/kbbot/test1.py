import sys
from kb import KB, Boolean, Integer, Constant

# Define our symbols
A = Boolean('A')
B = Boolean('B')
C = Boolean('C')

# Create a new knowledge base
kb = KB()

# Add clauses
kb.add_clause(A, B, C)
kb.add_clause(~A, B)
kb.add_clause(~B, C)
kb.add_clause(B, ~C)

# Print all models of the knowledge base
for model in kb.models():
    print(model)

# Print out whether the KB is satisfiable (if there are no models, it is not satisfiable)
print(kb.satisfiable())
