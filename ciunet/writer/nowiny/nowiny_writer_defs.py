# .\nowiny_writer_defs.py
# -*- coding: utf-8 -*-
# PyXB bindings for NM:e92452c8d3e28a9e27abfc9994d2007779e7f4c9
# Generated 2017-10-25 09:00:43.653212 by PyXB version 1.2.6 using Python 3.6.3.final.0
# Namespace AbsentNamespace0

from __future__ import unicode_literals
import pyxb
import pyxb.binding
import pyxb.binding.saxer
import io
import pyxb.utils.utility
import pyxb.utils.domutils
import sys
import pyxb.utils.six as _six
# Unique identifier for bindings created at the same time
_GenerationUID = pyxb.utils.utility.UniqueIdentifier('urn:uuid:38011424-b952-11e7-bef1-94c6911586b3')

# Version of PyXB used to generate the bindings
_PyXBVersion = '1.2.6'
# Generated bindings are not compatible across PyXB versions
if pyxb.__version__ != _PyXBVersion:
    raise pyxb.PyXBVersionError(_PyXBVersion)

# A holder for module-level binding classes so we can access them from
# inside class definitions where property names may conflict.
_module_typeBindings = pyxb.utils.utility.Object()
# Import bindings for namespaces imported into schema
#import pyxb.binding.datatypes
# NOTE: All namespace declarations are reserved within the binding
Namespace = pyxb.namespace.CreateAbsentNamespace()
Namespace.configureCategories(['typeBinding', 'elementBinding'])

def CreateFromDocument (xml_text, default_namespace=None, location_base=None):
    """Parse the given XML and use the document element to create a
    Python instance.

    @param xml_text An XML document.  This should be data (Python 2
    str or Python 3 bytes), or a text (Python 2 unicode or Python 3
    str) in the L{pyxb._InputEncoding} encoding.

    @keyword default_namespace The L{pyxb.Namespace} instance to use as the
    default namespace where there is no default namespace in scope.
    If unspecified or C{None}, the namespace of the module containing
    this function will be used.

    @keyword location_base: An object to be recorded as the base of all
    L{pyxb.utils.utility.Location} instances associated with events and
    objects handled by the parser.  You might pass the URI from which
    the document was obtained.
    """

    if pyxb.XMLStyle_saxer != pyxb._XMLStyle:
        dom = pyxb.utils.domutils.StringToDOM(xml_text)
        return CreateFromDOM(dom.documentElement, default_namespace=default_namespace)
    if default_namespace is None:
        default_namespace = Namespace.fallbackNamespace()
    saxer = pyxb.binding.saxer.make_parser(fallback_namespace=default_namespace, location_base=location_base)
    handler = saxer.getContentHandler()
    xmld = xml_text
    if isinstance(xmld, _six.text_type):
        xmld = xmld.encode(pyxb._InputEncoding)
    saxer.parse(io.BytesIO(xmld))
    instance = handler.rootObject()
    return instance

def CreateFromDOM (node, default_namespace=None):
    """Create a Python instance from the given DOM node.
    The node tag must correspond to an element declaration in this module.

    @deprecated: Forcing use of DOM interface is unnecessary; use L{CreateFromDocument}."""
    if default_namespace is None:
        default_namespace = Namespace.fallbackNamespace()
    return pyxb.binding.basis.element.AnyCreateFromDOM(node, default_namespace)


# Complex type [anonymous] with content type ELEMENT_ONLY
class CTD_ANON (pyxb.binding.basis.complexTypeDefinition):
    """Complex type [anonymous] with content type ELEMENT_ONLY"""
    _TypeDefinition = None
    _ContentTypeTag = pyxb.binding.basis.complexTypeDefinition._CT_ELEMENT_ONLY
    _Abstract = False
    _ExpandedName = None
    _XSDLocation = pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 6, 4)
    _ElementMap = {}
    _AttributeMap = {}
    # Base type is pyxb.binding.datatypes.anyType
    
    # Element IdKiln uses Python identifier IdKiln
    __IdKiln = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'IdKiln'), 'IdKiln', '__AbsentNamespace0_CTD_ANON_IdKiln', False, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 8, 8), )

    
    IdKiln = property(__IdKiln.value, __IdKiln.set, None, None)

    
    # Element Date uses Python identifier Date
    __Date = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'Date'), 'Date', '__AbsentNamespace0_CTD_ANON_Date', False, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 9, 8), )

    
    Date = property(__Date.value, __Date.set, None, None)

    
    # Element Sections uses Python identifier Sections
    __Sections = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'Sections'), 'Sections', '__AbsentNamespace0_CTD_ANON_Sections', False, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 10, 8), )

    
    Sections = property(__Sections.value, __Sections.set, None, None)

    _ElementMap.update({
        __IdKiln.name() : __IdKiln,
        __Date.name() : __Date,
        __Sections.name() : __Sections
    })
    _AttributeMap.update({
        
    })
_module_typeBindings.CTD_ANON = CTD_ANON


# Complex type [anonymous] with content type ELEMENT_ONLY
class CTD_ANON_ (pyxb.binding.basis.complexTypeDefinition):
    """Complex type [anonymous] with content type ELEMENT_ONLY"""
    _TypeDefinition = None
    _ContentTypeTag = pyxb.binding.basis.complexTypeDefinition._CT_ELEMENT_ONLY
    _Abstract = False
    _ExpandedName = None
    _XSDLocation = pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 11, 10)
    _ElementMap = {}
    _AttributeMap = {}
    # Base type is pyxb.binding.datatypes.anyType
    
    # Element Section uses Python identifier Section
    __Section = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'Section'), 'Section', '__AbsentNamespace0_CTD_ANON__Section', True, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 19, 14), )

    
    Section = property(__Section.value, __Section.set, None, None)

    _ElementMap.update({
        __Section.name() : __Section
    })
    _AttributeMap.update({
        
    })
_module_typeBindings.CTD_ANON_ = CTD_ANON_


# Complex type [anonymous] with content type ELEMENT_ONLY
class CTD_ANON_2 (pyxb.binding.basis.complexTypeDefinition):
    """Complex type [anonymous] with content type ELEMENT_ONLY"""
    _TypeDefinition = None
    _ContentTypeTag = pyxb.binding.basis.complexTypeDefinition._CT_ELEMENT_ONLY
    _Abstract = False
    _ExpandedName = None
    _XSDLocation = pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 20, 16)
    _ElementMap = {}
    _AttributeMap = {}
    # Base type is pyxb.binding.datatypes.anyType
    
    # Element Position uses Python identifier Position
    __Position = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'Position'), 'Position', '__AbsentNamespace0_CTD_ANON_2_Position', False, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 22, 20), )

    
    Position = property(__Position.value, __Position.set, None, '\n                          Middle position of Section on the kiln. Unit=millimeters\n                        ')

    
    # Element Temps uses Python identifier Temps
    __Temps = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'Temps'), 'Temps', '__AbsentNamespace0_CTD_ANON_2_Temps', False, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 29, 20), )

    
    Temps = property(__Temps.value, __Temps.set, None, None)

    _ElementMap.update({
        __Position.name() : __Position,
        __Temps.name() : __Temps
    })
    _AttributeMap.update({
        
    })
_module_typeBindings.CTD_ANON_2 = CTD_ANON_2


# Complex type [anonymous] with content type ELEMENT_ONLY
class CTD_ANON_3 (pyxb.binding.basis.complexTypeDefinition):
    """Complex type [anonymous] with content type ELEMENT_ONLY"""
    _TypeDefinition = None
    _ContentTypeTag = pyxb.binding.basis.complexTypeDefinition._CT_ELEMENT_ONLY
    _Abstract = False
    _ExpandedName = None
    _XSDLocation = pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 30, 22)
    _ElementMap = {}
    _AttributeMap = {}
    # Base type is pyxb.binding.datatypes.anyType
    
    # Element temp uses Python identifier temp
    __temp = pyxb.binding.content.ElementDeclaration(pyxb.namespace.ExpandedName(None, 'temp'), 'temp', '__AbsentNamespace0_CTD_ANON_3_temp', True, pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 39, 26), )

    
    temp = property(__temp.value, __temp.set, None, '\n                                Unit=°Celsius\n                              ')

    _ElementMap.update({
        __temp.name() : __temp
    })
    _AttributeMap.update({
        
    })
_module_typeBindings.CTD_ANON_3 = CTD_ANON_3


TempMeas = pyxb.binding.basis.element(pyxb.namespace.ExpandedName(Namespace, 'TempMeas'), CTD_ANON, location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 5, 2))
Namespace.addCategoryObject('elementBinding', TempMeas.name().localName(), TempMeas)



CTD_ANON._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'IdKiln'), pyxb.binding.datatypes.integer, scope=CTD_ANON, location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 8, 8)))

CTD_ANON._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'Date'), pyxb.binding.datatypes.dateTime, scope=CTD_ANON, location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 9, 8)))

CTD_ANON._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'Sections'), CTD_ANON_, scope=CTD_ANON, location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 10, 8)))

def _BuildAutomaton ():
    # Remove this helper function from the namespace after it is invoked
    global _BuildAutomaton
    del _BuildAutomaton
    import pyxb.utils.fac as fac

    counters = set()
    states = []
    final_update = None
    symbol = pyxb.binding.content.ElementUse(CTD_ANON._UseForTag(pyxb.namespace.ExpandedName(None, 'IdKiln')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 8, 8))
    st_0 = fac.State(symbol, is_initial=True, final_update=final_update, is_unordered_catenation=False)
    states.append(st_0)
    final_update = None
    symbol = pyxb.binding.content.ElementUse(CTD_ANON._UseForTag(pyxb.namespace.ExpandedName(None, 'Date')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 9, 8))
    st_1 = fac.State(symbol, is_initial=False, final_update=final_update, is_unordered_catenation=False)
    states.append(st_1)
    final_update = set()
    symbol = pyxb.binding.content.ElementUse(CTD_ANON._UseForTag(pyxb.namespace.ExpandedName(None, 'Sections')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 10, 8))
    st_2 = fac.State(symbol, is_initial=False, final_update=final_update, is_unordered_catenation=False)
    states.append(st_2)
    transitions = []
    transitions.append(fac.Transition(st_1, [
         ]))
    st_0._set_transitionSet(transitions)
    transitions = []
    transitions.append(fac.Transition(st_2, [
         ]))
    st_1._set_transitionSet(transitions)
    transitions = []
    st_2._set_transitionSet(transitions)
    return fac.Automaton(states, counters, False, containing_state=None)
CTD_ANON._Automaton = _BuildAutomaton()




CTD_ANON_._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'Section'), CTD_ANON_2, scope=CTD_ANON_, location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 19, 14)))

def _BuildAutomaton_ ():
    # Remove this helper function from the namespace after it is invoked
    global _BuildAutomaton_
    del _BuildAutomaton_
    import pyxb.utils.fac as fac

    counters = set()
    cc_0 = fac.CounterCondition(min=240, max=240, metadata=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 19, 14))
    counters.add(cc_0)
    states = []
    final_update = set()
    final_update.add(fac.UpdateInstruction(cc_0, False))
    symbol = pyxb.binding.content.ElementUse(CTD_ANON_._UseForTag(pyxb.namespace.ExpandedName(None, 'Section')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 19, 14))
    st_0 = fac.State(symbol, is_initial=True, final_update=final_update, is_unordered_catenation=False)
    states.append(st_0)
    transitions = []
    transitions.append(fac.Transition(st_0, [
        fac.UpdateInstruction(cc_0, True) ]))
    st_0._set_transitionSet(transitions)
    return fac.Automaton(states, counters, False, containing_state=None)
CTD_ANON_._Automaton = _BuildAutomaton_()




CTD_ANON_2._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'Position'), pyxb.binding.datatypes.integer, scope=CTD_ANON_2, documentation='\n                          Middle position of Section on the kiln. Unit=millimeters\n                        ', location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 22, 20)))

CTD_ANON_2._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'Temps'), CTD_ANON_3, scope=CTD_ANON_2, location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 29, 20)))

def _BuildAutomaton_2 ():
    # Remove this helper function from the namespace after it is invoked
    global _BuildAutomaton_2
    del _BuildAutomaton_2
    import pyxb.utils.fac as fac

    counters = set()
    states = []
    final_update = None
    symbol = pyxb.binding.content.ElementUse(CTD_ANON_2._UseForTag(pyxb.namespace.ExpandedName(None, 'Position')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 22, 20))
    st_0 = fac.State(symbol, is_initial=True, final_update=final_update, is_unordered_catenation=False)
    states.append(st_0)
    final_update = set()
    symbol = pyxb.binding.content.ElementUse(CTD_ANON_2._UseForTag(pyxb.namespace.ExpandedName(None, 'Temps')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 29, 20))
    st_1 = fac.State(symbol, is_initial=False, final_update=final_update, is_unordered_catenation=False)
    states.append(st_1)
    transitions = []
    transitions.append(fac.Transition(st_1, [
         ]))
    st_0._set_transitionSet(transitions)
    transitions = []
    st_1._set_transitionSet(transitions)
    return fac.Automaton(states, counters, False, containing_state=None)
CTD_ANON_2._Automaton = _BuildAutomaton_2()




CTD_ANON_3._AddElement(pyxb.binding.basis.element(pyxb.namespace.ExpandedName(None, 'temp'), pyxb.binding.datatypes.integer, scope=CTD_ANON_3, documentation='\n                                Unit=°Celsius\n                              ', location=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 39, 26)))

def _BuildAutomaton_3 ():
    # Remove this helper function from the namespace after it is invoked
    global _BuildAutomaton_3
    del _BuildAutomaton_3
    import pyxb.utils.fac as fac

    counters = set()
    cc_0 = fac.CounterCondition(min=36, max=64, metadata=pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 39, 26))
    counters.add(cc_0)
    states = []
    final_update = set()
    final_update.add(fac.UpdateInstruction(cc_0, False))
    symbol = pyxb.binding.content.ElementUse(CTD_ANON_3._UseForTag(pyxb.namespace.ExpandedName(None, 'temp')), pyxb.utils.utility.Location('C:\\Users\\sc\\dev\\projects\\CIU-NETx\\ciunet\\writer\\nowiny\\nowiny_writer.xsd', 39, 26))
    st_0 = fac.State(symbol, is_initial=True, final_update=final_update, is_unordered_catenation=False)
    states.append(st_0)
    transitions = []
    transitions.append(fac.Transition(st_0, [
        fac.UpdateInstruction(cc_0, True) ]))
    st_0._set_transitionSet(transitions)
    return fac.Automaton(states, counters, False, containing_state=None)
CTD_ANON_3._Automaton = _BuildAutomaton_3()

