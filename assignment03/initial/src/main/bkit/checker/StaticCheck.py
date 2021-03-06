
"""
 * @author nhphung
"""
from abc import ABC, abstractmethod, ABCMeta
from dataclasses import dataclass
from typing import List, Tuple
from AST import *
from Visitor import *
from StaticError import *
from functools import *


class Type(ABC):
    __metaclass__ = ABCMeta
    pass


class Prim(Type):
    __metaclass__ = ABCMeta
    pass


class IntType(Prim):
    pass


class FloatType(Prim):
    pass


class StringType(Prim):
    pass


class BoolType(Prim):
    pass


class VoidType(Type):
    pass


class Unknown(Type):
    pass


@dataclass
class ArrayType(Type):
    dimen: List[int]
    eletype: Type


@dataclass
class MType:
    intype: List[Type]
    restype: Type


@dataclass
class Symbol:
    name: str
    mtype: Type
    kind: Kind


class StaticChecker(BaseVisitor):
    def __init__(self, ast):
        self.ast = ast
        self.global_envi = [
            Symbol("int_of_float", MType(
                [FloatType()], IntType()), Function()),
            Symbol("float_of_int", MType(
                [IntType()], FloatType()), Function()),
            Symbol("int_of_string", MType(
                [StringType()], IntType()), Function()),
            Symbol("string_of_int", MType(
                [IntType()], StringType()), Function()),
            Symbol("float_of_string", MType(
                [StringType()], FloatType()), Function()),
            Symbol("string_of_float", MType(
                [FloatType()], StringType()), Function()),
            Symbol("bool_of_string", MType(
                [StringType()], BoolType()), Function()),
            Symbol("string_of_bool", MType(
                [BoolType()], StringType()), Function()),
            Symbol("read", MType([], StringType()), Function()),
            Symbol("printLn", MType([], VoidType()), Function()),
            Symbol("printStr", MType([StringType()], VoidType()), Function()),
            Symbol("printStrLn", MType([StringType()], VoidType()), Function())]

    @staticmethod
    def getDictionary():
        typeDict = {}
        typeDict = {op: {'inType': IntType(), 'outType': IntType()}
                    for op in ['+', '-', '*', '-']}
        typeDict.update({op: {'inType': FloatType(), 'outType': FloatType()}
                         for op in ['+.', '-.', '*.', '/.']})
        typeDict.update({op: {'inType': BoolType(), 'outType': BoolType()}
                         for op in ['&&', '||', '!']})
        typeDict.update({op: {'inType': IntType(), 'outType': BoolType()}
                         for op in ['>', '<', '>=', '<=', '==', '!=']})
        typeDict.update({op: {'inType': FloatType(), 'outType': BoolType()}
                         for op in ['>.', '<.', '>=.', '<=.', '=/=']})
        return typeDict

    def getSymbol(self, _name, scope):
        for e in scope:
            if e.name == _name:
                return e
        return

    def getSymbolIndex(self, _name, scope):
        for i in range(len(scope)):
            if scope[i].name == _name:
                return i

    def checkRedeclared(self, symbol, scope):
        for e in scope:
            if e.name == symbol.name:
                raise Redeclared(symbol.kind, symbol.name)

    def checkUndeclared(self, _name, scope, _kind=Identifier()):
        for e in scope:
            if e.name == _name:
                return
        raise Undeclared(_kind, _name)

    def checkEntryPoint(self, globalScope):
        for e in globalScope:
            if isinstance(e.kind, Function) and e.name == "main":
                return
        raise NoEntryPoint()

    def check(self):
        return self.visit(self.ast, self.global_envi)

    def isNameInScope(self, _name, list):
        for e in list:
            if _name == e.name:
                return True
        return False

    def directInfer(self, e, _type, scope):
        if isinstance(e, Id):
            self.getSymbol(e.name, scope).mtype = _type
        elif isinstance(e, CallExpr):
            self.getSymbol(e.method.name, scope).mtype = _type
        elif isinstance(e, ArrayCell):
            pass

    def updateSymbolType(self, _name, scope, _type):
        for e in scope:
            if _name == e.name:
                if isinstance(e.mtype, Type):
                    e.mtype = _type
                else:
                    e.mtype.restype = _type
                return True
        return False

    # name: str
    def visitId(self, ast, c):
        self.checkUndeclared(ast.name, c, Variable())
        _symbol = self.getSymbol(ast.name, c)
        return _symbol.mtype

    # decl:List[Decl]
    def visitProgram(self, ast, c):
        # Need to check entry point before visiting the children
        for e in ast.decl:
            if isinstance(e, VarDecl):
                _var = Symbol(e.variable.name, Unknown(), Variable())
                self.checkRedeclared(_var, c)
                c.append(_var)
            elif isinstance(e, FuncDecl):
                _paramList = []
                _func = Symbol(e.name.name, MType(
                    _paramList, Unknown()), Function())
                self.checkRedeclared(_func, c)
                c.append(_func)
        self.checkEntryPoint(c)
        [self.visit(x, c) for x in ast.decl]

    # variable : Id
    # varDimen : List[int] # empty list for scalar variable
    # varInit  : Literal   # null if no initial
    def visitVarDecl(self, ast, c):
        varType = Unknown()
        if len(ast.varDimen) != 0:
            if ast.varInit != None:
                elementType = self.visit(ast.varInit, c)
                varType = ArrayType(ast.varDimen, elementType)
            else:
                varType = ArrayType(ast.varDimen, Unknown())
        elif ast.varInit != None:
            varType = self.visit(ast.varInit, c)

        # Update type of symbol in scope
        for symbol in c:
            if symbol.name == ast.variable.name:
                symbol.mtype = varType

    # name: Id
    # param: List[VarDecl]
    # body: Tuple[List[VarDecl],List[Stmt]]
    def visitFuncDecl(self, ast, c):
        paramList = []
        for currentParam in ast.param:
            _param = Symbol(currentParam.variable.name, Unknown(), Parameter())
            self.checkRedeclared(_param, paramList)
            paramList.append(_param)
            self.visit(currentParam, c)

        varList = paramList.copy()
        for currentVarDecl in ast.body[0]:
            _var = Symbol(currentVarDecl.variable.name, Unknown(), Variable())
            self.checkRedeclared(_var, varList)
            varList.append(_var)
            self.visit(currentVarDecl, c)

        # Making local scope including global symbol which is not declared in local
        localScope = varList.copy()
        localScopeHavingGlobalOnly = []  # Make it faster to update global symbol later
        for symbolGlobal in c:
            if not self.isNameInScope(symbolGlobal.name, localScope):
                localScope.append(symbolGlobal)
                localScopeHavingGlobalOnly.append(symbolGlobal)

        [self.visit(_stmt, localScope) for _stmt in ast.body[1]]

        #  Update type of global symbol
        for symbolGlobal in c:
            if self.isNameInScope(symbolGlobal.name, localScopeHavingGlobalOnly) and isinstance(symbolGlobal.mtype, Unknown):
                symbolLocal = self.getSymbol(
                    symbolGlobal.name, localScope)
                symbolGlobal.mtype = symbolLocal.mtype

    # arr:Expr
    # idx:List[Expr]
    def visitArrayCell(self, ast, c):
        pass

    # op:str
    # left:Expr
    # right:Expr
    def visitBinaryOp(self, ast, c):
        _op = ast.op
        lhsType = self.visit(ast.left, c)
        rhsType = self.visit(ast.right, c)
        typeDict = self.getDictionary()

        if isinstance(lhsType, Unknown):
            if isinstance(ast.left, Id):
                lhsType = typeDict[_op]['inType']
                self.updateSymbolType(
                    ast.left.name, c, typeDict[_op]['inType'])
            elif isinstance(ast.left, CallExpr):
                lhsType = typeDict[_op]['inType']
                self.updateSymbolType(
                    ast.left.method.name, c, typeDict[_op]['inType'])
            elif isinstance(ast.left, ArrayCell):
                pass

        if isinstance(rhsType, Unknown):
            if isinstance(ast.right, Id):
                rhsType = typeDict[_op]['inType']
                self.updateSymbolType(
                    ast.right.name, c, typeDict[_op]['inType'])
            elif isinstance(ast.right, CallExpr):
                rhsType = typeDict[_op]['inType']
                self.updateSymbolType(
                    ast.right.method.name, c, typeDict[_op]['inType'])
            elif isinstance(ast.left, ArrayCell):
                pass

        if lhsType != typeDict[ast.op]['inType'] or rhsType != typeDict[ast.op]['inType']:
            raise TypeMismatchInExpression(ast)

        return typeDict[_op]['outType']

    # op:str
    # body:Expr
    def visitUnaryOp(self, ast, c,):
        _op = ast.op
        bodyType = self.visit(ast.body, c)
        typeDict = self.getDictionary()
        if isinstance(bodyType, Unknown):
            if isinstance(ast.body, Id):
                bodyType = typeDict[_op]['inType']
                self.updateSymbolType(
                    ast.body.name, c, typeDict[_op]['inType'])
            elif isinstance(ast.body, CallExpr):
                bodyType = typeDict[_op]['inType']
                self.updateSymbolType(
                    ast.body.method.name, c, typeDict[_op]['inType'])
            elif isinstance(ast.left, ArrayCell):
                pass

        if bodyType != typeDict[ast.op]['inType']:
            raise TypeMismatchInExpression(ast)

        return typeDict[_op]['outType']

    # method:Id
    # param:List[Expr]
    def visitCallExpr(self, ast, c):
        self.checkUndeclared(ast.method.name, c, Function())
        _callExprType = self.visit(ast.method, c)
        if not isinstance(_callExprType.restype, VoidType) or len(ast.param) != len(_callExprType.intype):
            raise TypeMismatchInExpression(ast)

        _callExpr = self.getSymbol(ast.method.name, c)
        argsTypeList = [self.visit(_param, c) for _param in ast.param]

        for i in range(len(ast.param)):
            _argType = argsTypeList[i]
            _callExprIntype = _callExpr.mtype.intype[i]
            if type(_argType) is Unknown:
                if type(_callExprIntype) is Unknown:
                    return TypeCannotBeInferred()
                else:
                    argIndex = self.getSymbolIndex(
                        ast.param[i].name, c)
                    c[argIndex].mtype = _callExprIntype
                    argsTypeList[i] = _callExprIntype
            else:
                if type(_callExprIntype) is Unknown:
                    _callExprIndex = self.getSymbolIndex(
                        _callExpr.name, c)
                    c[_callExprIndex].mtype.intype[i] = _argType
                    _callExpr.mtype.intype[i] = _argType
                elif type(_argType) != type(_callExprIntype):
                    raise TypeMismatchInExpression(ast)
        return _callExpr.mtype.restype

    # value:int
    def visitIntLiteral(self, ast, c):
        return IntType()

    # value:float
    def visitFloatLiteral(self, ast, c):
        return FloatType()

    # value: string
    def visitStringLiteral(self, ast, c):
        return StringType()

    # value:bool
    def visitBooleanLiteral(self, ast, c):
        return BoolType()

    # value:List[Literal]
    def visitArrayLiteral(self, ast, c):
        # if len(ast.value) == 0:
        #     return Unknown()
        # _value = [self.visit(e, c) for e in ast.value]
        # return _value[0]
        pass

    # lhs: LHS
    # rhs: Expr
    def visitAssign(self, ast, c):
        lhsType = self.visit(ast.lhs, c)
        rhsType = self.visit(ast.rhs, c)
        if isinstance(lhsType, VoidType):
            raise TypeMismatchInStatement(ast)

        resultType = Unknown
        if isinstance(lhsType, Unknown) and isinstance(rhsType, Unknown):
            raise TypeCannotBeInferred(ast)
        elif isinstance(lhsType, Unknown) and not isinstance(rhsType, Unknown):
            resultType = rhsType
        elif not isinstance(lhsType, Unknown) and isinstance(rhsType, Unknown):
            resultType = lhsType
        elif type(lhsType) != type(rhsType):
            raise TypeMismatchInExpression(ast)

        self.directInfer(ast.lhs, resultType, c)
        self.directInfer(ast.rhs, resultType, c)

        return resultType

    # ifthenStmt:List[Tuple[Expr,List[VarDecl],List[Stmt]]]
    # elseStmt:Tuple[List[VarDecl],List[Stmt]] # for Else branch, empty list if no Else
    def visitIf(self, ast, c):
        # visiting if, and elseIf
        for i in range(len(ast.ifthenStmt)):
            expType = self.visit(ast.ifthenStmt[i][0], c)
            if not isinstance(expType, BoolType):
                raise TypeMismatchInStatement(ast)

            varList = []
            for currentVarDecl in ast.ifthenStmt[i][1]:
                _var = Symbol(currentVarDecl.variable.name,
                              Unknown(), Variable())
                self.checkRedeclared(_var, varList)
                varList.append(_var)
                self.visit(currentVarDecl, c)

            localScope = varList.copy()
            localScopeHavingGlobalOnly = []  # Make it faster to update global symbol later
            for symbolGlobal in c:
                if not self.isNameInScope(symbolGlobal.name, localScope):
                    localScope.append(symbolGlobal)
                    localScopeHavingGlobalOnly.append(symbolGlobal)

            [self.visit(_stmt, localScope) for _stmt in ast.ifthenStmt[i][2]]

        # visiting else
        varList = []
        for currentVarDecl in ast.elseStmt[0]:
            _var = Symbol(currentVarDecl.variable.name, Unknown(), Variable())
            self.checkRedeclared(_var, varList)
            varList.append(_var)
            self.visit(currentVarDecl, c)

        localScope = varList.copy()
        localScopeHavingGlobalOnly = []  # Make it faster to update global symbol later
        for symbolGlobal in c:
            if not self.isNameInScope(symbolGlobal.name, localScope):
                localScope.append(symbolGlobal)
                localScopeHavingGlobalOnly.append(symbolGlobal)

        [self.visit(_stmt, localScope) for _stmt in ast.elseStmt[1]]

    # idx1: Id
    # expr1:Expr
    # expr2:Expr
    # expr3:Expr
    # loop: Tuple[List[VarDecl],List[Stmt]]

    def visitFor(self, ast, c):
        _idx1 = Symbol(ast.idx1.name, Unknown(), Variable())
        c.append(_idx1)
        self.visit(ast.idx1, c)
        expr1Type = self.visit(ast.expr1, c)
        expr2Type = self.visit(ast.expr2, c)
        expr3Type = self.visit(ast.expr3, c)

        if not isinstance(expr1Type, IntType) or not isinstance(expr3Type, IntType) or not isinstance(expr2Type, BoolType):
            raise TypeMismatchInStatement(ast)

        varList = []
        for currentVarDecl in ast.loop[0]:
            _var = Symbol(currentVarDecl.variable.name, Unknown(), Variable())
            self.checkRedeclared(_var, varList)
            varList.append(_var)
            self.visit(currentVarDecl, c)

        localScope = varList.copy()
        localScopeHavingGlobalOnly = []  # Make it faster to update global symbol later
        for symbolGlobal in c:
            if not self.isNameInScope(symbolGlobal.name, localScope):
                localScope.append(symbolGlobal)
                localScopeHavingGlobalOnly.append(symbolGlobal)

        [self.visit(_stmt, localScope) for _stmt in ast.loop[1]]

    def visitBreak(self, ast, c):
        pass

    def visitContinue(self, ast, c):
        pass

    # expr:Expr # None if no expression
    def visitReturn(self, ast, c):
        expType = self.visit(ast.expr, c)
        pass

    # sl:Tuple[List[VarDecl],List[Stmt]]
    # exp: Expr
    def visitDowhile(self, ast, c):
        varList = []
        for currentVarDecl in ast.sl[0]:
            _var = Symbol(currentVarDecl.variable.name, Unknown(), Variable())
            self.checkRedeclared(_var, varList)
            varList.append(_var)
            self.visit(currentVarDecl, c)

        localScope = varList.copy()
        localScopeHavingGlobalOnly = []  # Make it faster to update global symbol later
        for symbolGlobal in c:
            if not self.isNameInScope(symbolGlobal.name, localScope):
                localScope.append(symbolGlobal)
                localScopeHavingGlobalOnly.append(symbolGlobal)

        [self.visit(_stmt, localScope) for _stmt in ast.sl[1]]

        expType = self.visit(ast.exp, localScope)
        if not isinstance(expType, BoolType):
            raise TypeMismatchInStatement(ast)

    # exp: Expr
    # sl:Tuple[List[VarDecl],List[Stmt]]
    def visitWhile(self, ast, c):
        expType = self.visit(ast.exp, c)
        if not isinstance(expType, BoolType):
            raise TypeMismatchInStatement(ast)

        varList = []
        for currentVarDecl in ast.sl[0]:
            _var = Symbol(currentVarDecl.variable.name, Unknown(), Variable())
            self.checkRedeclared(_var, varList)
            varList.append(_var)
            self.visit(currentVarDecl, c)

        localScope = varList.copy()
        localScopeHavingGlobalOnly = []  # Make it faster to update global symbol later
        for symbolGlobal in c:
            if not self.isNameInScope(symbolGlobal.name, localScope):
                localScope.append(symbolGlobal)
                localScopeHavingGlobalOnly.append(symbolGlobal)

        [self.visit(_stmt, localScope) for _stmt in ast.sl[1]]

    # method:Id
    # param:List[Expr]
    def visitCallStmt(self, ast, c):
        self.checkUndeclared(ast.method.name, c, Function())
        callStmtType = self.visit(ast.method, c)
        if len(ast.param) != len(callStmtType.intype):
            raise TypeMismatchInStatement(ast)

        _callStmt = self.getSymbol(ast.method.name, c)
        argsTypeList = [self.visit(_param, c) for _param in ast.param]

        for i in range(len(ast.param)):
            _argType = argsTypeList[i]
            _callExprIntype = _callStmt.mtype.intype[i]
            if type(_argType) is Unknown:
                if type(_callExprIntype) is Unknown:
                    return TypeCannotBeInferred()
                else:
                    argIndex = self.getSymbolIndex(
                        ast.param[i].name, c)
                    c[argIndex].mtype = _callExprIntype
                    argsTypeList[i] = _callExprIntype
            else:
                if type(_callExprIntype) is Unknown:
                    _callExprIndex = self.getSymbolIndex(
                        _callStmt.name, c)
                    c[_callExprIndex].mtype.intype[i] = _argType
                    _callStmt.mtype.intype[i] = _argType
                elif type(_argType) != type(_callExprIntype):
                    raise TypeMismatchInExpression(ast)
