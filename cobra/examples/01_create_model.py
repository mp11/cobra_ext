#cobra/examples/01_create_model.py
#
#This file provides a simple example of how to create a model and
#then create a reaction and add it to the model.
#
#
#  For this example, we'll use the '3 oxoacyl acyl carrier protein synthase n C140 '
# reaction from the STM_1.0 model which currently has the ID of '3OAS140':
#  
# 1.0 malACP[c] + 1.0 h[c] + 1.0 ddcaACP[c] -> 1.0 co2[c] + 1.0 ACP[c] + 1.0 3omrsACP[c]
#
from cobra import Model, Reaction, Metabolite
cobra_model = Model('example_cobra_model') #Best practise is to use SBML compliant IDs

reaction = Reaction('3OAS140')
reaction.name = '3 oxoacyl acyl carrier protein synthase n C140 '
reaction.subsystem = 'Cell Envelope Biosynthesis'
reaction.lower_bound = 0. #This is the default
reaction.upper_bound = 1000. #This is the default
reaction.reversibility = 0 #This is the default
reaction.objective_coefficient = 0. #this is the default
#Adding metabolites to a reaction requires using a dictionary of the metabolites and
#their stoichiometric coefficients.  A group of metabolites can be added all at once or
#the can be added one at a time.
#Create the metabolites
ACP_c = Metabolite('ACP_c', formula='C11H21N2O7PRS', name='acyl-carrier-protein', compartment='c')
omrsACP_c = Metabolite('3omrsACP_c', formula='C25H45N2O9PRS', name='3-Oxotetradecanoyl-acyl-carrier-protein', compartment='c')
co2_c = Metabolite('co2_c', formula='CO2', name='CO2', compartment='c')
malACP_c = Metabolite('malACP_c', formula='C14H22N2O10PRS', name='Malonyl-acyl-carrier-protein', compartment='c')
h_c = Metabolite('h_c', formula='H', name='H', compartment='c')
ddcaACP_c = Metabolite('ddcaACP_c', formula='C23H43N2O8PRS', name='Dodecanoyl-ACP-n-C120ACP', compartment='c') 

#add the metabolites to the reaction:
reaction.add_metabolites({malACP_c: -1.0,
                          h_c: -1.0,
                          ddcaACP_c: -1.0,
                          co2_c: 1.0,
                          ACP_c: 1.0,
                          omrsACP_c: 1.0})

#Print the reaction to make sure it worked:
print reaction.reaction

reaction.gene_reaction_rule = '( STM2378  or  STM1197 )'
#The next step will create cobra.Gene objects from the gene reaction rule, which will
#be used later by the cobra.Model to modulate reaction bounds after deleting genes.
reaction.parse_gene_association()

#The model's initially empty:
print '%i reactions in model'%len(cobra_model.reactions)
print '%i metabolites in model'%len(cobra_model.metabolites)
print '%i genes in model'%len(cobra_model.genes)


#Add the reaction to the model
cobra_model.add_reactions(reaction)

#Now there are things in the model
print '%i reaction in model'%len(cobra_model.reactions)
print '%i metabolites in model'%len(cobra_model.metabolites)
print '%i genes in model'%len(cobra_model.genes)

for x in cobra_model.reactions:
    print x.reaction
for x in cobra_model.metabolites:
    print '%s has formula %s'%(x,x.formula)
for x in cobra_model.genes:
    print 'gene %s is associated with reactions:'%x
    for y in x._reaction:
        print '\t%s'%y
