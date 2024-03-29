#cobra.core.Reaction.py
#######################
#BEGIN Class Reaction
#
from collections import defaultdict
import re
from copy import deepcopy
from .Object import Object
from .Metabolite import Metabolite
from .Gene import Gene
class Reaction(Object):
    """Reaction is a class for holding information regarding
    a biochemical reaction in a cobra.Model object 

    """
    ## __slots__ = ['id', 'reversibility', '_metabolites', 'gene_reaction_rule',
    ##              'subsystem', '_genes', '_model',
    ##              'name', 'lower_bound', 'upper_bound', 'objective_coefficient',
    ##              'reaction', 'boundary']

    def __init__(self, name=None):
        """An object for housing reactions and associated information
        for cobra modeling..

        boundary: Boolean.  Indicates whether the reaction is at a boundary, i.e.,
        a source or a sink.
        
        """
        Object.__init__(self, name)
        self.reversibility = 0 #Deprecated.  This is determined by the lower
        #and upper bound
        self.gene_reaction_rule = '' #Deprecated
        self.subsystem = ''
        self._genes = {} #A gene and the number of copies required for the
        #reaction.  _ Indicates that it is not preferred to add a gene to a reaction
        #directly.
        #A dictionary of metabolites and their stoichiometric coefficients in
        #this reaction  _ Indicates that it is not preferred to add a metabolite to a reaction
        #directly.
        self._metabolites = {}
        self._boundary_metabolites = {} #Book keeping for boundary metabolites
        #DEPRECATED: _id_to_metabolites = {} #Caution this may not always be up to date
        #if self._metabolites is modified
        self.name = name
        #self.model is None or refers to the cobra.Model that
        #contains self
        self._model  = self.reaction = None

        self.boundary = None #None, 'system_boundary'
        self.objective_coefficient = self.lower_bound = 0.
        self.upper_bound = 1000.
        self.reflection = None #Either None or if this reaction is irreversible then
        #a reaction in the model that is essentially self * -1
        self.variable_kind = 'continuous' #Used during optimization.  Indicates whether the
        #variable is modeled as continuous, integer, binary, semicontinous, or semiinteger.

    def _update_awareness(self):
        """Make sure all metabolites and genes that are associated with
        this reaction are aware of it.
        
        """
        [x._reaction.add(self) for x in self._metabolites]
        [x._reaction.add(self) for x in self._genes]

    def remove_from_model(self, model=None):
        """Removes the association

        model: cobra.Model object.  remove the reaction from this model.
        
        """
        # why is model being taken in as a parameter?
        if model != self._model and model is not None:
            raise Exception('%s not in %s ergo it cannot be removed. (%s)'%(self,
                                                                  model,
                                                                  self._model))
                                                            
        new_metabolites = deepcopy(self._metabolites)
        new_genes = deepcopy(self._genes)
        self._model.reactions.remove(self)
        #Remove associations between the reaction and its container _model
        #and elements in the model
        self._model = None
        [x._reaction.remove(self)
         for x in self._metabolites.keys()]
        [x._reaction.remove(self)
         for x in self._genes.keys()]
        self.add_metabolites(new_metabolites)
        self._genes = new_genes

    def delete(self):
        """Removes all associations between a reaction and its container
        _model and metabolites and genes.
        
        TODO: Decide whether orphan metabolites should automatically be removed
        from the model.
        
        """
        self._model = None
        [x._reaction.remove(self)
         for x in self._metabolites.keys()]
        [x._reaction.remove(self)
         for x in self._genes.keys()]
        self._metabolites = {}
        self._genes = {}
        
    def __setstate__(self, state):
        """Probably not necessary to set _model as the cobra.Model that
        contains self sets the _model attribute for all metabolites and genes in the reaction.

        However, to increase performance speed we do want to let the metabolite and gene
        know that they are employed in this reaction

        """
        self.__dict__.update(state)
        for x in state['_metabolites']:
            setattr(x, '_model', self._model)
            x._reaction.add(self)
        for x in state['_genes']:
            setattr(x, '_model', self._model)
            x._reaction.add(self)

    
    def copy(self):
        """When copying a reaction, it is necessary to deepcopy the
        components so the list references aren't carried over.

        Additionally, a copy of a reaction is no longer in a cobra.Model.

        This should be fixed with self.__deecopy__ if possible
        """
        ## the_model = self._model
        ## self._model = None
        new_reaction = deepcopy(self)
        ## self._model = the_model
        return new_reaction
    def guided_copy(self, the_model, metabolite_dict, gene_dict=None):
        """Trying to make a faster copy procedure for cases where large
        numbers of metabolites might be copied.  Such as when copying reactions.

        """
        the_copy = Object.guided_copy(self)
        #Replace the complex items in a faster fashion
        the_copy._model = the_model
        if gene_dict:
            the_copy._genes = dict([(gene_dict[k.id], v)
                                for k, v in self._genes.items()])
        the_copy._metabolites = dict([(metabolite_dict[k.id], v)
                                      for k, v in self._metabolites.items()])
        the_copy._boundary_metabolites = dict([(metabolite_dict[k.id], v)
                                               for k, v in self._boundary_metabolites.items()])

        #make the metabolites and genes aware of the reaction
        [k._reaction.add(the_copy)
         for k in the_copy._genes.keys()]
        [k._reaction.add(the_copy)
         for k in the_copy._metabolites.keys()]
        [k._reaction.add(the_copy)
         for k in the_copy._boundary_metabolites.keys()]
        return(the_copy)

    def pop(self, the_metabolite):
        """Remove a metabolite from the reaction and return the
        stoichiometric coefficient.

        the_metabolite: A cobra.Metabolite that is in the reaction
    
        
        """
        the_coefficient = self._metabolites.pop(the_metabolite)
        the_metabolite._reaction.remove(self)
        self.reconstruct_reaction()
        return the_coefficient
    
    def __add__(self, other_reaction):
        """Adds two reactions to each other.  Default behavior is
        to combine the metabolites but only use the remaining parameters
        from the first object.

        TODO: Deal with gene association logic from adding reactions.

        TODO: Simplify and add in an __iadd__
        
        """
        new_reaction = deepcopy(self)
        new_reaction.id = self.id + '_' + other_reaction.id
        new_reaction.add_metabolites(deepcopy(other_reaction._metabolites))
        new_reaction._genes.update(deepcopy(other_reaction._genes))
        #Make all the genes aware of this reaction
        [x._reaction.add(new_reaction) for x in new_reaction._genes]
        gpr_1 = new_reaction.gene_reaction_rule
        gpr_2 = other_reaction.gene_reaction_rule
        if gpr_1 != '' and gpr_2 != '':
            new_reaction.gene_reaction_rule = '%s and %s'%(gpr_1, gpr_2)
        elif gpr_2 != '':
            new_reaction.gene_reaction_rule = gpr_2
        return new_reaction
    
    def __sub__(self, other_reaction):
        """Subtracts two reactions.  Default behavior is
        to combine the metabolites but only use the remaining parameters
        from the first object.

        Note: This is equivalent to adding reactions after changing the sign
        of the metabolites in other_reaction
        
        """
        new_reaction = deepcopy(self)
        if self is other_reaction:
            other_reaction = deepcopy(other_reaction)
        new_reaction.id = self.id + '_' + other_reaction.id
        new_reaction.subtract_metabolites(deepcopy(other_reaction._metabolites))
        return new_reaction

    def __imul__(self, the_coefficient):
        """Allows the reaction coefficients to be rapidly scaled.
        
        """
        [self._metabolites.update({k: the_coefficient * v})
         for k, v in self._metabolites.items()]
        self.reconstruct_reaction()
        return self

    def __mul__(self, the_coefficient):
        """Allows a reaction to be multipled by a coeffient.
        
        Should this return a new reaction?
        
        """
        [self._metabolites.update({k: the_coefficient * v})
         for k, v in self._metabolites.items()]
        self.reconstruct_reaction()
        return self
        

    def parse_gene_association(self, the_type='gene'):
        """Extract all genes from the Boolean Gene_Association string.

        #Formerly, update_names
        """
        if the_type == 'gene':
            self._genes = map(Gene, list(set((re.compile(' {2,}').sub(' ', re.compile('\(| and| or|\+|\)').sub('', self.gene_reaction_rule))).split(' ' ))))
            if '' in self._genes:
                self._genes.remove('')
            self._genes = dict(zip(self._genes,[1.]*len(self._genes)))
            #Make the gene aware that it is involved in this reaction
            [x._reaction.add(self) for x in self._genes]

    def get_reactants(self):
        """Return a list of reactants for the reaction.

        """
        return [k for k, v in self._metabolites.items()
                if v < 0]

    def get_products(self):
        """Return a list of products for the reaction
        
        """
        return [k for k, v in self._metabolites.items()
                if v > 0]


    def get_coefficient(self, the_metabolite):
        """Return the stoichiometric coefficient for a metabolite in
        the reaction.

        the_metabolite: A metabolite Id.
        
        """
        _id_to_metabolites = dict([(x.id, x)
                                        for x in self._metabolites])

        if hasattr(the_metabolite, 'id'):
            the_metabolite = the_metabolite.id
        return self._metabolites[_id_to_metabolites[the_metabolite]]
    
    def get_coefficients(self, the_metabolites):
        """Return the stoichiometric coefficients for a list of
        metabolites in the reaction.

        the_metabolites:  A list of metabolite Ids.
        
        """
        return map(self.get_coefficient, the_metabolites)
    
    def add_metabolites(self, the_metabolites, combine=True, add_to_container_model=True):
        """Add metabolites and stoichiometric coefficients to the reaction.
        If the final coefficient for a metabolite is 0 then it is removed
        from the reaction.

        the_metabolites: A dict of cobra.Metabolites and their coefficient

        combine: Boolean. If True and a metabolite already exists in the
        reaction then the coefficients will be added.  If False the old
        metabolite will be discarded and the new one added.

        add_to_container_model: Boolean.  If True and this reaction is
        contained within a cobra.Model (i.e., self._model is a cobra.Model)
        then add the metabolite to the model.

        """
        _id_to_metabolites = dict([(x.id, x)
                                        for x in self._metabolites])
        new_metabolites = []
        for the_metabolite, the_coefficient in the_metabolites.items():
            #If a metabolite already exists in the reaction then
            #just add them.
            if the_metabolite.id in _id_to_metabolites:
                reaction_metabolite = _id_to_metabolites[the_metabolite.id]
                if combine:
                    self._metabolites[reaction_metabolite] += the_coefficient
                else:
                    self._metabolites[reaction_metabolite] = the_coefficient
            else:
                self._metabolites[the_metabolite] = the_coefficient
                #make the metabolite aware that it is involved in this reaction
                the_metabolite._reaction.add(self)
                new_metabolites.append(the_metabolite)
        for the_metabolite, the_coefficient in self._metabolites.items():
            if the_coefficient == 0:
                #make the metabolite aware that it no longer participates
                #in this reaction
                the_metabolite._reaction.remove(self)
                self._metabolites.pop(the_metabolite)
        self.reconstruct_reaction()
        _id_to_metabolites = dict([(x.id, x)
                                        for x in self._metabolites])
        if add_to_container_model and hasattr(self._model, 'add_metabolites'):
            self._model.add_metabolites(new_metabolites)
            

    def subtract_metabolites(self, metabolites):
        """This function will 'subtract' cobra.metabolites from a reaction, which
        means add the metabolites with -1*coefficient.  If the final coefficient
        for a metabolite is 0 then the metabolite is removed from the reaction.

        .. note:: That a final coefficient < 0 implies a reactant.

        metabolites: dict of {:class:`~cobra.core.Metabolite`: coefficient}
            These metabolites will be added to the reaction

        .. note:: This function uses deepcopy in case the reaction is being
        subtracted from itself.
        
        """
        metabolites = deepcopy(metabolites)
        metabolites = dict([(k, -v)
                                for k, v in metabolites.items()])
        self.add_metabolites(metabolites)

        
    def _parse_reaction(self):
        """
        This is necessary when parsing text files.  It is better
        to get the reactions from SBML files.

        WARNING: this needs to be updated to deal with non-palssonesqe reactions.
        """
        raise Exception('WARNING: this needs to be updated to deal with non-palssonesqe reactions.')
        if not self.id:
            print 'Reaction has not been populated.'
            return
        #remove parentheses around stoichiometric coefficients
        re_stoich_coeff = re.compile('\(\d+\.{0,1}\d{0,}\)')
        re_spaces = re.compile(' {2,} ')
        the_reaction = re_spaces.subn(' ', self.reaction)[0]
        tmp_reaction = ''
        for the_atom in the_reaction.split(' '):
            tmp_reaction += ' '
            if re_stoich_coeff.match(the_atom) is not None:
                the_atom = the_atom.lstrip('(').rstrip(')')
            tmp_reaction += the_atom
        self.reaction = tmp_reaction[1:]
        if self.reaction[0] == '[' and self.reaction[2] ==']':
            self.process_prefixed_reaction()
        #Deal with scientific notation here
        tmp_metabolites = re.compile('\d*\.?\d+(e-?\d)? +').sub('', self.reaction)
        tmp_metabolites = re.compile('( *\+ *)|( *<*(-+|=+)> *)').sub('\t', tmp_metabolites).split('\t')
      
        #TODO: Can the user specifying the reversibility override the reaction equation?
        #(i.e. If self.reversibility != '' then do the following? )
        #Change the reversible check to a regular expression
        if ' <=> ' in self.reaction or ' <==> ' in self.reaction:
            self.reversibility = 1
            reaction_delimiter_re = re.compile(' +<=+> +')
        elif ' <-> ' in self.reaction or ' <--> ' in self.reaction:
            self.reversibility = 1
            reaction_delimiter_re = re.compile(' +<-+> +')
        elif '-> ' in  self.reaction:
            self.reversibility = 0
            reaction_delimiter_re = re.compile(' +-+> +')
        elif '<- ' in  self.reaction:
            self.reversibility = 0
            reaction_delimiter_re = re.compile(' +<-+ +')

        [tmp_reactants, tmp_products] = reaction_delimiter_re.split(self.reaction)
        element_re = re.compile(' +\+ +')
        tmp_reactants = element_re.split(tmp_reactants)
        tmp_products = element_re.split(tmp_products)
        tmp_coefficients = []
        for the_reactant in tmp_reactants:
            tmp_split = the_reactant.split(' ')
            if len(tmp_split) > 1:
                tmp_coefficients.append(-1*float(tmp_split[0]))
            else:
                tmp_coefficients.append(-1)
        for the_product in tmp_products:
            tmp_split = the_product.split(' ')
            if len(tmp_split) > 1:
                tmp_coefficients.append(float(tmp_split[0]))
            else:
                tmp_coefficients.append(1)
        self._metabolites = dict([(Metabolite('%s_%s'%(x[:-3],
                                                       x[-2]),
                                              compartment=x[-2]), y)
                                 for x, y in zip(tmp_metabolites, tmp_coefficients)])
        #Make the metabolites aware of participating in this reaction
        [x._reaction.add(self) for x in self._metabolites]

    def build_reaction_string(self, use_metabolite_names=False):
        """Generate a human readable reaction string.
        
        """
        reactant_dict = {}
        product_dict = {}
        id_type = 'id'
        if use_metabolite_names:
            id_type = 'name'
        for the_metabolite, the_coefficient in self._metabolites.items():
            the_key = str(getattr(the_metabolite, id_type))
            if the_coefficient > 0:
                product_dict[the_key] = repr(the_coefficient)
            else:
                reactant_dict[the_key] = repr(abs(the_coefficient))
        reaction_string = ''
        for the_key in reactant_dict:
            reaction_string += ' + %s %s'%(reactant_dict[the_key],
                                         the_key)
        if self.reversibility == 0:
            if self.lower_bound < 0 and self.upper_bound <=0:
                reaction_string += ' <- '
            else:
                reaction_string += ' -> '                
        else:
            reaction_string += ' <=> '
        for the_key in product_dict:
            reaction_string += "%s %s + "%(product_dict[the_key],
                                      the_key)
        reaction_string = reaction_string.lstrip(' + ').rstrip(' + ')
        return reaction_string

        
    def reconstruct_reaction(self):
        """Generate a human readable reaction string.
        
        """
        if not self.id:
            print 'Reaction has not been populated.'
            return

        if len(self._metabolites) == 0:
            self.reaction = None
        else:
            self.reaction = self.build_reaction_string()

    def check_mass_balance(self):
        """Makes sure that the reaction is elementally-balanced.

        """
        reaction_element_dict = defaultdict(list)
        for the_metabolite, the_coefficient in self._metabolites.items():
            if the_metabolite.formula is not None:
                [reaction_element_dict[k].append(the_coefficient*v)
                 for k, v in the_metabolite.formula.elements.items()]
        reaction_element_dict = dict([(k, sum(v))
                                      for k, v in reaction_element_dict.items()])
        if sum(map(abs, reaction_element_dict.values())) != 0:
            return [self.id, reaction_element_dict]
        else:
            return []
        
    def print_values(self):
        """Prints most of the contents of a reaction as a series of strings.
        
        """
        if not self.id:
            print 'Reaction has not been populated.'
            return
        for the_item in [self.reaction, [(k.id, v)
                                         for k, v in self._metabolites.items()],
                         self.reversibility, self.lower_bound, self.upper_bound,
                         self.objective_coefficient, self.subsystem,
                         self.gene_reaction_rule, [x.id for x in self._genes],
                         self._metabolites]:
            print repr(the_item)

#DEPRECATED SECTION
    def process_prefixed_reaction(self):
        """Deal with reaction names that have a prefix.

        DEPRECATED
        This is necessary when parsing text files.  It is better
        to get the reactions from SBML files.

        This can be moved to a tools section
        
        """
        from warnings import warn
        warn('Reaction.process_prefixed_reaction is deprecated')
        the_compartment, the_reaction = self.reaction.split(':')
        the_compartment = the_compartment.rstrip(' ')
        the_reaction = the_reaction.lstrip(' ')
        re_spaces = re.compile(' {2,} ')
        the_reaction = re_spaces.subn(' ', the_reaction)[0]
        the_atoms = the_reaction.split(' ')
        re_director = re.compile('( *<*(-+|=+)> *)')
        re_stoich_coeff = re.compile('^\d+\.?\d*$')
        new_reaction = ''
        for the_atom in the_atoms:
            new_reaction += ' '
            if the_atom != '+' and re_director.match(the_atom) is None \
                   and re_stoich_coeff.match(the_atom) is None:
                the_atom += the_compartment
            new_reaction += the_atom
        self.reaction = new_reaction[1:]

#
#END Class Reaction
########################
